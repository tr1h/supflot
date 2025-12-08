# -*- coding: utf-8 -*-
"""
SUP Booking — продакшн-подобный сайт в одном файле.

Запуск:
    python app.py runserver 8000

ENV:
    DB_NAME=/path/to/SupBot.db
    ADMIN_IDS=202140267,1383730017
    SECRET_KEY=...
    PLATFORM_COMMISSION_PERCENT=10

    # Платежи
    YOOKASSA_SHOP_ID=1096529
    YOOKASSA_SECRET_KEY=live_kkeCU7ALrCJ_ViiVMPSGYWS3svDUuU445bXyKzUE3sM
    PAYMENT_CARD_DETAILS="Перевод на карту XXXX XXXX XXXX XXXX ФИО"

    # Карта (по умолчанию — Кремль, Москва)
    MAP_DEFAULT_LAT=55.751244
    MAP_DEFAULT_LON=37.618423
    MAP_DEFAULT_ZOOM=11
    YMAPS_API_KEY=...   # можно не указывать — тоже работает
"""

import os, sys, json, csv, base64, uuid, hmac, hashlib
from datetime import datetime, timedelta, date

from django.conf import settings
from django.core.management import execute_from_command_line, call_command
from django.db import connections, transaction
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotFound, JsonResponse
from django.shortcuts import render, redirect
from django.urls import path, re_path
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

# -----------------------------
# Django settings (one-file)
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.environ.get("DB_NAME") or os.path.join(os.path.dirname(BASE_DIR), "SupBot.db")
SECRET = os.environ.get("SECRET_KEY", "sup-landing-dev-secret")

if not settings.configured:
    settings.configure(
        DEBUG = os.environ.get("DEBUG", "0") == "1",
        SECRET_KEY=SECRET,
        ROOT_URLCONF=__name__,
        ALLOWED_HOSTS=["*"],
        USE_TZ=False,
        TIME_ZONE="Europe/Moscow",
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.sessions",
            "django.contrib.messages",
            "django.contrib.staticfiles",
        ],
        MIDDLEWARE=[
            "django.middleware.security.SecurityMiddleware",
            "django.middleware.common.CommonMiddleware",
            "django.middleware.csrf.CsrfViewMiddleware",
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.contrib.messages.middleware.MessageMiddleware",
        ],
        TEMPLATES=[{
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "DIRS": [],
            "APP_DIRS": False,
            "OPTIONS": {
                "context_processors": [
                    "django.template.context_processors.request",
                    "django.contrib.messages.context_processors.messages",
                ],
                "loaders": [("django.template.loaders.locmem.Loader", {
                    # ================== TEMPLATES ==================
                    "base.html": r'''
<!doctype html>
<html lang="ru">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>{% block title %}SUP Booking{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
      :root { --brand:#0ea5e9; --ink:#0f172a; --muted:#6b7280 }
      body { padding: 24px; background:#f6f9fc; color:var(--ink) }
      .navbar-brand { font-weight: 800; letter-spacing:.2px }
      .muted { color:var(--muted) }
      .tile { border-radius: 14px; background:#fff; padding:18px; box-shadow:0 2px 12px rgba(2,6,23,.06) }
      .hero { padding: 40px 28px; border-radius: 16px; margin-bottom: 24px;
              background: radial-gradient(1200px 400px at 10% -10%, #e0f2fe 0%, transparent 60%),
                          radial-gradient(1200px 400px at 90% 10%, #cffafe 0%, transparent 60%),
                          #ffffff; box-shadow:0 6px 24px rgba(2,6,23,.08) }
      .stat-lg { font-weight:800; font-size:1.6rem; line-height:1 }
      .badge-soft { background:#e0f2fe; color:#0c4a6e }
      .btn-brand { background:var(--brand); border-color:var(--brand) }
      .btn-brand:hover { filter:brightness(.96) }
      .table td,.table th { vertical-align: middle }
      .footer { color:#6b7280 }
      #map { width:100%; height: 420px; border-radius:14px; box-shadow:0 2px 12px rgba(2,6,23,.06); }
      #pickmap { width:100%; height: 300px; border-radius:12px; box-shadow:0 2px 12px rgba(2,6,23,.06); }
      .catalog-card { border-radius:14px; box-shadow:0 1px 10px rgba(2,6,23,.06) }
      .chip { background:#eef6ff; color:#0b4a6f; border-radius:999px; padding:2px 8px; font-size:.82rem }
      .hero-img { border-radius:12px; max-width:100%; height:auto; box-shadow:0 8px 28px rgba(2,6,23,.12) }
      form.inline { display:inline }
    </style>
  </head>
  <body>
    <nav class="navbar navbar-expand-lg bg-body-tertiary mb-4 rounded shadow-sm px-3">
      <a class="navbar-brand" href="/">SUP Booking</a>
      <div class="navbar-nav">
        <a class="nav-link" href="/#mapwrap">Карта</a>
        <a class="nav-link" href="/#book">Бронирование</a>
        <a class="nav-link" href="/about/">О нас</a>
        {% if request.session.tg_id %}
          <a class="nav-link" href="/user/{{ request.session.tg_id }}/">Кабинет</a>
          <a class="nav-link" href="/partner/{{ request.session.tg_id }}/">Партнёр</a>
          <a class="nav-link" href="/employee/{{ request.session.tg_id }}/">Сотрудник</a>
          <a class="nav-link" href="/admin/{{ request.session.tg_id }}/">Админ</a>
          <a class="nav-link" href="/logout/">Выйти</a>
        {% else %}
          <a class="nav-link" href="/signup/">Регистрация</a>
          <a class="nav-link" href="/login/">Войти</a>
        {% endif %}
      </div>
    </nav>
    <div class="container">
      {% block content %}{% endblock %}
      <div class="text-center mt-5 footer small">© {{ now|default:0|date:"Y" }} SUP Booking. Любим воду и сервис.</div>
    </div>
  </body>
</html>
''',

                    "auth.html": r'''
{% extends "base.html" %}
{% block title %}Вход/регистрация{% endblock %}
{% block content %}
  <div class="row justify-content-center">
    <div class="col-md-6">
      <div class="card shadow-sm">
        <div class="card-body">
          <h4 class="mb-3">Войти</h4>
          <form method="post" action="/login/">{% csrf_token %}
            <div class="mb-2">
              <label class="form-label">Ваш Telegram ID</label>
              <input class="form-control" name="tg_id" required>
            </div>
            <div class="mb-3">
              <label class="form-label">Роль</label>
              <select class="form-select" name="role">
                <option value="user">Пользователь</option>
                <option value="partner">Партнёр</option>
                <option value="employee">Сотрудник</option>
                <option value="admin">Админ</option>
              </select>
            </div>
            <button class="btn btn-brand">Войти</button>
          </form>
          <hr>
          <h5>Регистрация (создаст профиль пользователя)</h5>
          <form method="post" action="/signup/">{% csrf_token %}
            <div class="row g-2">
              <div class="col-md-6">
                <input class="form-control" name="tg_id" placeholder="Telegram ID" required>
              </div>
              <div class="col-md-6">
                <input class="form-control" name="username" placeholder="username (опц.)">
              </div>
              <div class="col-12">
                <input class="form-control" name="full_name" placeholder="Имя (опц.)">
              </div>
              <div class="col-12">
                <input class="form-control" name="phone" placeholder="Телефон (опц.)">
              </div>
              <div class="col-12 d-grid">
                <button class="btn btn-outline-primary">Зарегистрироваться</button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
{% endblock %}
''',

                    # ================== LANDING ==================
                    "index.html": r'''
{% extends "base.html" %}
{% block title %}SUPFLOT — аренда SUP-досок с картой, мгновенной бронью и безопасной оплатой{% endblock %}
{% block content %}

  <style>
    :root { --brand:#0ea5e9; --ink:#0f172a; --muted:#6b7280 }
    .hero {
      position:relative; overflow:hidden;
      padding:70px 28px; border-radius:22px; margin-bottom:28px;
      background:
        radial-gradient(1200px 350px at 5% -20%, rgba(14,165,233,.18), transparent 60%),
        radial-gradient(900px 320px at 120% 10%, rgba(6,182,212,.18), transparent 60%),
        linear-gradient(180deg,#ffffff 0%, #f7fbff 100%);
      box-shadow:0 22px 60px rgba(2,6,23,.12);
    }
    .headline{ font-weight:900; letter-spacing:.2px; line-height:1.02; text-wrap:balance }
    .accent{
      background: linear-gradient(90deg, #0ea5e9, #22d3ee);
      -webkit-background-clip:text; background-clip:text; color:transparent;
    }
    .kpi{ display:inline-flex; align-items:center; gap:10px; padding:8px 14px; border-radius:999px;
          font-weight:700; font-size:.95rem; background:#eaf6ff; color:#084b6d; box-shadow:inset 0 0 0 1px rgba(14,165,233,.20) }
    .kpi .dot{ width:8px; height:8px; border-radius:50%; background:var(--brand) }
    .meta { display:flex; gap:10px; flex-wrap:wrap; margin-top:12px }
    .chip { background:#eef6ff; color:#0b4a6f; border-radius:999px; padding:4px 10px; font-size:.86rem }
    .rating { display:inline-flex; align-items:center; gap:6px; background:#fff; padding:6px 10px; border-radius:999px; box-shadow:0 2px 10px rgba(2,6,23,.06) }

    .btn-cta{ padding:12px 18px; font-weight:800; border-width:2px }
    .btn-brand{ background:var(--brand); border-color:var(--brand) }
    .btn-cta:hover{ transform:translateY(-1px); transition:all .15s ease }

    #map { width:100%; height:500px; border-radius:18px; box-shadow:0 10px 34px rgba(2,6,23,.10) }
    .card-modern { border-radius:18px; box-shadow:0 10px 34px rgba(2,6,23,.08) }
    .sticky-book { position:sticky; top:16px }
    .divider { height:1px; background:linear-gradient(90deg,transparent,#e5e7eb,transparent); margin:16px 0 }

    .benefit { display:flex; gap:12px; align-items:flex-start; padding:14px 16px; border-radius:14px; background:#f6fbff; border:1px solid #e7f3ff }
    .benefit .ic { font-size:1.2rem }
    .usp { border:1px solid #edf2f7; border-radius:14px; padding:14px; background:#fff }
    .logos { display:flex; gap:14px; flex-wrap:wrap; color:#0b4a6f }
    .logos .lo { padding:6px 10px; background:#eef6ff; border-radius:10px; font-weight:700 }

    .testi { background:#fff; border:1px solid #edf2f7; border-radius:14px; padding:14px }
    .banner-cta {
      margin-top:24px; border-radius:18px; padding:30px 20px;
      background: radial-gradient(600px 220px at 100% -10%, rgba(14,165,233,.16), transparent 60%), #ffffff;
      box-shadow:0 12px 36px rgba(2,6,23,.10);
    }
    .small-muted{ color:#6b7280; font-size:.92rem }
  </style>

  <!-- HERO -->
  <div class="hero">
    <div class="row align-items-center g-4">
      <div class="col-lg-7">
        <div class="mb-3">
          <span class="kpi"><span class="dot"></span> Новый сезон · брони открыты</span>
          <span class="rating ms-2">⭐ 4.9 · 1000+ поездок прошлым летом</span>
        </div>
        <h1 class="headline mb-3">
          SUPFLOT — аренда SUP-досок <span class="accent">за пару кликов</span>
        </h1>
        <p class="text-muted mb-4">
          Карта локаций с живым наличием и честной ценой. Мгновенная бронь, безопасная онлайн-оплата, выдача на месте.
        </p>
        <div class="d-flex gap-3 flex-wrap">
          <a href="#mapwrap" class="btn btn-outline-secondary btn-cta">Открыть карту</a>
          <a href="#book" class="btn btn-brand btn-cta">Забронировать</a>
        </div>
        <div class="meta">
          <span class="chip">Локаций: <b>{{ stat.locations }}</b></span>
          <span class="chip">Досок: <b>{{ stat.boards }}</b></span>
          <span class="chip">Активных сегодня: <b>{{ stat.active }}</b></span>
          <span class="chip">Оплата · YooKassa</span>
          <span class="chip">Гарантия погоды</span>
        </div>
      </div>
      <div class="col-lg-5 text-center">
        <picture>
          <img class="hero-img" alt="SUP"
               style="border-radius:14px; max-width:100%; height:auto; box-shadow:0 12px 40px rgba(2,6,23,.16)"
               src="https://images.unsplash.com/photo-1558981403-c5f9899a28bf?q=80&w=1200&auto=format&fit=crop"
               onerror="this.style.display='none'">
        </picture>
      </div>
    </div>
  </div>

  <!-- TRUST / LOGOS -->
  <div class="logos mb-3">
    <div class="lo">✅ Безопасная оплата</div>
    <div class="lo">🧭 Понятная выдача/сдача</div>
    <div class="lo">📸 Фото до/после</div>
    <div class="lo">🧑‍🚀 Поддержка в Telegram</div>
  </div>

  <div class="row g-4">
    <!-- MAP -->
    <div class="col-lg-7">
      <div id="mapwrap" class="d-flex justify-content-between align-items-center mb-2">
        <h5 class="m-0">🗺️ Карта предложений</h5>
        <div class="small text-muted">Жмите на пин — откроется витрина партнёра</div>
      </div>
      <div class="card card-modern">
        <div class="card-body p-2 p-sm-3"><div id="map"></div></div>
      </div>

      <!-- 4 ключевые выгоды -->
      <div class="row g-3 mt-3">
        <div class="col-md-6"><div class="benefit"><div class="ic">💸</div><div><b>Честная цена</b><div class="text-muted small">динамически от спроса и времени</div></div></div></div>
        <div class="col-md-6"><div class="benefit"><div class="ic">🛡️</div><div><b>Прозрачные условия</b><div class="text-muted small">сразу видно что, где и за сколько</div></div></div></div>
        <div class="col-md-6"><div class="benefit"><div class="ic">⚡</div><div><b>Мгновенная бронь</b><div class="text-muted small">оплата онлайн — и готово</div></div></div></div>
        <div class="col-md-6"><div class="benefit"><div class="ic">🏁</div><div><b>Выдача на месте</b><div class="text-muted small">сотрудник встречает, всё быстро</div></div></div></div>
      </div>
    </div>

    <!-- BOOKING (sticky) -->
    <div class="col-lg-5" id="book">
      <div class="card card-modern sticky-book">
        <div class="card-body">
          <div class="d-flex align-items-center justify-content-between">
            <h5 class="card-title m-0">⚡ Забронировать</h5>
            <span class="badge text-bg-light">1–2 мин</span>
          </div>
          <div class="divider"></div>

          <!-- hourly -->
          <form method="post" action="/book/">
            {% csrf_token %}
            <input type="hidden" name="mode" value="hourly">
            <div class="row g-2">
              <div class="col-md-6">
                <label class="form-label">Локация</label>
                <select class="form-select" name="location_id" id="selLocation" required>
                  <option value="" disabled selected>Выберите локацию…</option>
                  {% for l in locations %}<option value="{{ l.id }}">{{ l.name }}</option>{% endfor %}
                </select>
              </div>
              <div class="col-md-6">
                <label class="form-label">Доска</label>
                <select class="form-select" name="board_id" id="selBoard" required>
                  <option value="" disabled selected>Выберите доску…</option>
                  {% for b in boards %}
                    <option value="{{ b.id }}" data-loc="{{ b.location_id }}">#{{ b.id }} · {{ b.name }} — от {{ b.price|floatformat:0 }} ₽/ч (всего {{ b.total }})</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">Дата</label>
                <input type="date" name="date" class="form-control" value="{{ today }}" required>
              </div>
              <div class="col-md-4">
                <label class="form-label">Начало</label>
                <input type="time" name="start" class="form-control" value="10:00" required>
              </div>
              <div class="col-md-4">
                <label class="form-label">Часов</label>
                <input type="number" name="hours" min="1" max="12" value="2" class="form-control" required>
              </div>

              <div class="col-md-6">
                <label class="form-label">Кол-во досок</label>
                <input type="number" name="qty" min="1" value="1" class="form-control" required>
              </div>
              <div class="col-md-6">
                <label class="form-label">Купон (если есть)</label>
                <input name="coupon" class="form-control" placeholder="PROMO10">
              </div>

              <div class="col-12 small-muted">
                Цена может меняться от спроса. Свободные окна считаются с учётом пересечений.
              </div>

              <div class="col-md-7">
                <label class="form-label">Ваш Telegram ID</label>
                <input type="number" name="tg_id" value="{{ request.session.tg_id|default_if_none:'' }}" class="form-control" required>
              </div>
              <div class="col-md-5 d-grid">
                <button class="btn btn-brand btn-lg mt-4 mt-md-0" type="submit">Забронировать</button>
              </div>
            </div>
          </form>

          <div class="divider"></div>

          <!-- daily -->
          <h6 class="mb-2">🛍️ Суточная аренда</h6>
          <form method="post" action="/book/">
            {% csrf_token %}
            <input type="hidden" name="mode" value="daily">
            <div class="row g-2">
              <div class="col-md-6">
                <select class="form-select" name="daily_board_id" required>
                  <option value="" selected disabled>Предложение…</option>
                  {% for d in daily_offers %}
                    <option value="{{ d.id }}">#{{ d.id }} · {{ d.name }} — {{ d.price|floatformat:0 }} ₽/сутки</option>
                  {% endfor %}
                </select>
              </div>
              <div class="col-md-3"><input type="date" name="date" class="form-control" value="{{ today }}" required></div>
              <div class="col-md-3"><input type="number" name="days" min="1" max="14" value="1" class="form-control"></div>
              <div class="col-md-6"><input name="coupon" class="form-control" placeholder="Купон (если есть)"></div>
              <div class="col-md-6"><input type="number" name="tg_id" value="{{ request.session.tg_id|default_if_none:'' }}" class="form-control" placeholder="Ваш Telegram ID" required></div>
              <div class="col-12 d-grid">
                <button class="btn btn-outline-primary" type="submit">Забронировать на сутки</button>
              </div>
            </div>
          </form>

          <div class="divider"></div>

          <!-- мини-лонгрид как это работает -->
          <div class="vstack gap-2">
            <div class="benefit"><div class="ic">🗺️</div><div><b>Выбираете локацию</b><div class="text-muted small">свободные окна и цена — сразу</div></div></div>
            <div class="benefit"><div class="ic">💳</div><div><b>Оплачиваете онлайн</b><div class="text-muted small">YooKassa/реквизиты — мгновенно</div></div></div>
            <div class="benefit"><div class="ic">📸</div><div><b>Фото до/после</b><div class="text-muted small">фиксируем состояние доски</div></div></div>
            <div class="benefit"><div class="ic">🌊</div><div><b>Катаетесь кайфуя</b><div class="text-muted small">поддержка рядом в Telegram</div></div></div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ПОЧЕМУ МЫ + ОТЗЫВЫ -->
  <div class="row g-4 mt-1">
    <div class="col-lg-7">
      <div class="card card-modern">
        <div class="card-body">
          <h5 class="m-0">Почему SUPFLOT</h5>
          <div class="divider"></div>
          <div class="row g-2">
            <div class="col-md-6"><div class="usp">⭐ Отобранные партнёры<br><span class="small-muted">витрины с прозрачными условиями</span></div></div>
            <div class="col-md-6"><div class="usp">🧾 Чеки и акты<br><span class="small-muted">документы в 1 клик</span></div></div>
            <div class="col-md-6"><div class="usp">🛰️ Карта и навигация<br><span class="small-muted">точка выдачи — на карте</span></div></div>
            <div class="col-md-6"><div class="usp">🛟 Безопасность и жилеты<br><span class="small-muted">инструктаж 2–3 минуты</span></div></div>
            <div class="col-md-6"><div class="usp">💬 Поддержка 7 дней/неделю<br><span class="small-muted">в Telegram</span></div></div>
            <div class="col-md-6"><div class="usp">🌦️ Гарантия погоды<br><span class="small-muted">перенос или возврат по правилам</span></div></div>
          </div>
        </div>
      </div>
    </div>
    <div class="col-lg-5">
      <div class="card card-modern">
        <div class="card-body">
          <h5 class="m-0">Отзывы</h5>
          <div class="divider"></div>
          <div class="vstack gap-2">
            <div class="testi">«Бронировали в день прогулки — 5 минут и готово. Карта удобная, на месте встретили вовремя.» — <b>Ирина</b>, ⭐⭐⭐⭐⭐</div>
            <div class="testi">«Цена честная, всё прозрачно. Фото до/после — класс, без споров.» — <b>Алексей</b>, ⭐⭐⭐⭐⭐</div>
            <div class="testi">«Катались на рассвете — это любовь. Оплата через YooKassa, быстро и спокойно.» — <b>Мария</b>, ⭐⭐⭐⭐⭐</div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ПАРТНЁРАМ -->
  <div class="card card-modern mt-4">
    <div class="card-body">
      <div class="row align-items-center g-3">
        <div class="col-lg-8">
          <h5 class="m-0">Партнёрам — подключайтесь за 1 день</h5>
          <div class="small-muted mt-1">Добавляйте локации и объявления (почас/сутки), настраивайте комиссию, выдавайте доступ сотрудникам.</div>
          <div class="meta mt-2">
            <span class="chip">🧾 Выплаты и отчётность</span>
            <span class="chip">🧑‍🔧 Мобильная выдача</span>
            <span class="chip">🏷️ Купоны и акции</span>
          </div>
        </div>
        <div class="col-lg-4 text-lg-end">
          <a class="btn btn-outline-dark btn-cta" href="/login/">Стать партнёром</a>
        </div>
      </div>
    </div>
  </div>

  <!-- FAQ -->
  <div class="row g-4 mt-1">
    <div class="col-lg-7">
      <div class="card card-modern">
        <div class="card-body">
          <h5 class="mb-2">Частые вопросы</h5>
          <div class="accordion" id="faq">
            <div class="accordion-item">
              <h2 class="accordion-header"><button class="accordion-button" type="button" data-bs-toggle="collapse" data-bs-target="#f1">Нужна ли подготовка?</button></h2>
              <div id="f1" class="accordion-collapse collapse show" data-bs-parent="#faq"><div class="accordion-body">Нет. Инструктаж занимает 2–3 минуты, выдадим весло, страховку и жилет.</div></div>
            </div>
            <div class="accordion-item">
              <h2 class="accordion-header"><button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#f2">Если плохая погода?</button></h2>
              <div id="f2" class="accordion-collapse collapse" data-bs-parent="#faq"><div class="accordion-body">Можно перенести бронь на доступное время или оформить возврат по правилам площадки.</div></div>
            </div>
            <div class="accordion-item">
              <h2 class="accordion-header"><button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#f3">Как связаться после оплаты?</button></h2>
              <div id="f3" class="accordion-collapse collapse" data-bs-parent="#faq"><div class="accordion-body">В личном кабинете появится заказ и контакт сотрудника для выдачи.</div></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Финальный баннер -->
    <div class="col-lg-5">
      <div class="banner-cta">
        <h5 class="mb-2">Готовы на воду? 🌊</h5>
        <div class="small-muted mb-3">Свободные окна есть сегодня. Бронь — за пару кликов, оплата — безопасно.</div>
        <a href="#book" class="btn btn-brand btn-cta">Забронировать сейчас</a>
      </div>
    </div>
  </div>

  <!-- MAP JS -->
  <script src="{{ ymaps_api }}"></script>
  <script>
    const MAP_LAT={{ map.lat }}; const MAP_LON={{ map.lon }}; const MAP_Z={{ map.zoom }};
    const markers = JSON.parse('{{ map.markers_json|escapejs }}');

    ymaps.ready(function() {
      const map = new ymaps.Map('map', {
        center:[MAP_LAT, MAP_LON], zoom: MAP_Z,
        controls:['zoomControl','geolocationControl','searchControl']
      });
      markers.forEach(m => {
        const preset = (m.kind === 'handover') ? 'islands#orangeIcon' : 'islands#blueIcon';
        const pm = new ymaps.Placemark([m.lat, m.lon], {
          balloonContent: `<div><b>${m.name}</b><br>
            от <b>${m.min_price}</b> ₽/ч · досок: ${m.total}<br>
            <a href="/owner/${m.partner_id}/" class="btn btn-sm btn-outline-primary mt-1">Открыть витрину</a></div>`
        }, { preset });
        map.geoObjects.add(pm);
      });
      if (markers.length) {
        const b = map.geoObjects.getBounds();
        if (b) map.setBounds(b, {checkZoomRange:true, zoomMargin:20});
      }
    });

    // фильтрация досок под выбранную локацию
    const selLocation = document.getElementById('selLocation');
    const selBoard = document.getElementById('selBoard');
    function filterBoards() {
      const loc = selLocation.value;
      [...selBoard.options].forEach((opt, idx) => {
        if (idx === 0) return;
        opt.hidden = !!loc && (opt.dataset.loc !== loc);
      });
      selBoard.value = '';
    }
    selLocation && selLocation.addEventListener('change', filterBoards);
  </script>
{% endblock %}
''',


                    # ABOUT
                    "about.html": r'''
{% extends "base.html" %}
{% block title %}О нас — SUP Booking{% endblock %}
{% block content %}
  <div class="row g-4">
    <div class="col-lg-8">
      <div class="card shadow-sm">
        <div class="card-body">
          <h4 class="card-title mb-3">О проекте</h4>
          <p>Маркетплейс проката SUP: карта предложений, прозрачные брони, онлайн-оплата, P2P-витрины владельцев и мобильная выдача.</p>
          <h5 class="mt-4">Контакты</h5>
          <ul class="list-unstyled text-muted">
            <li>Телеграм: <code>@sup_booking</code></li>
            <li>Почта: <code>hello@sup-booking.example</code></li>
            <li>Отзывы: <code>{{ reviews_channel|default:"@supflot_reviews" }}</code></li>
          </ul>
          <h5 class="mt-4">Партнёрам</h5>
          <p>Подключение за 1 день: добавляете локации и объявления (почас/сутки), настраиваете комиссию, выдаёте доступ сотрудникам.</p>
        </div>
      </div>
    </div>
    <div class="col-lg-4">
      <img class="img-fluid rounded shadow" alt="О нас" src="https://images.unsplash.com/photo-1598555642097-7b0190a7d2ac?q=80&w=1200&auto=format&fit=crop">
    </div>
  </div>
{% endblock %}
''',

                    # USER
                    "user.html": r'''
{% extends "base.html" %}
{% block title %}Кабинет пользователя{% endblock %}
{% block content %}
  <div class="d-flex align-items-center gap-3 mb-3">
    <h3 class="m-0">👤 Ваши брони</h3>
    <span class="badge text-bg-secondary">tg_id: {{ tg_id }}</span>
  </div>
  <div class="card shadow-sm">
    <div class="card-body">
      {% if bookings %}
        <div class="table-responsive">
          <table class="table table-sm">
            <thead><tr><th>#</th><th>Доска</th><th>Дата</th><th>Время</th><th>Часов</th><th>Кол-во</th><th>Сумма</th><th>Оплата</th><th>Статус</th><th></th></tr></thead>
            <tbody>
              {% for b in bookings %}
                <tr>
                  <td>{{ b.id }}</td>
                  <td>{{ b.board }}</td>
                  <td>{{ b.date }}</td>
                  <td>
                    {% if b.start_time is not None %}
                      {{ b.start_time|default:0 }}:{{ b.start_minute|default:0|stringformat:"02d" }}
                    {% else %}—{% endif %}
                  </td>
                  <td>{{ b.duration }}</td>
                  <td>{{ b.quantity }}</td>
                  <td>{{ b.amount|floatformat:0 }} ₽</td>
                  <td>
                    <span class="badge {% if b.payment_status == 'paid' %}text-bg-success{% elif b.payment_status == 'pending' %}text-bg-warning{% elif b.payment_status == 'failed' %}text-bg-danger{% else %}text-bg-secondary{% endif %}">
                      {{ b.payment_status|default:"unpaid" }}
                    </span>
                  </td>
                  <td>{{ b.status }}</td>
                  <td class="text-nowrap">
                    {% if b.payment_status != 'paid' and b.status in 'waiting_partner waiting_card waiting_cash waiting_daily' %}
                      <div class="btn-group btn-group-sm">
                        <a class="btn btn-outline-primary" href="/pay/{{ b.id }}/yookassa/">Оплатить ЮKassa</a>
                        <a class="btn btn-outline-secondary" href="/user/{{ tg_id }}/pay-card/{{ b.id }}/">Реквизиты</a>
                      </div>
                    {% endif %}
                    {% if b.status in 'waiting_partner waiting_card waiting_cash waiting_daily' %}
                      <form method="post" action="/user/{{ tg_id }}/cancel/{{ b.id }}/" class="inline">{% csrf_token %}
                        <button class="btn btn-outline-danger btn-sm" type="submit">Отменить</button>
                      </form>
                    {% endif %}
                  </td>
                </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      {% else %}
        <div class="text-muted">Пока пусто.</div>
      {% endif %}
    </div>
  </div>
{% endblock %}
''',

                    # PARTNER (включает выбор kind и карту-пикер)
                    "partner.html": r'''
{% extends "base.html" %}
{% block title %}Кабинет партнёра{% endblock %}
{% block content %}
  <div class="d-flex align-items-center gap-3 mb-3">
    <h3 class="m-0">👥 Партнёрский кабинет</h3>
    <span class="badge text-bg-secondary">tg_id: {{ tg_id }}</span>
    {% if partner_id %}<a class="btn btn-outline-dark btn-sm" href="/owner/{{ partner_id }}/">Витрина</a>{% endif %}
  </div>

  {% if partner_id %}
  <div class="row g-4">
    <!-- Wallet -->
    <div class="col-12 col-lg-4">
      <div class="card shadow-sm h-100">
        <div class="card-body">
          <div class="d-flex justify-content-between align-items-center">
            <h5 class="card-title m-0">💼 Кошелёк</h5>
            <span class="badge text-bg-success fs-6">{{ balance|floatformat:2 }} ₽</span>
          </div>
          <hr>
          <form method="post" action="/partner/{{ tg_id }}/withdraw/">
            {% csrf_token %}
            <label class="form-label">Сумма к выводу</label>
            <div class="input-group mb-2">
              <input name="amount" type="number" step="0.01" min="0" class="form-control" placeholder="500+">
              <button class="btn btn-outline-primary" type="submit">Запросить</button>
            </div>
            <div class="form-text">Минимум 500 ₽. Не чаще одного раза в 24 часа.</div>
          </form>
          {% if last_withdraws %}
          <hr>
          <div class="small text-muted">Последние заявки:</div>
          <ul class="list-group list-group-flush">
            {% for w in last_withdraws %}
              <li class="list-group-item d-flex justify-content-between">
                <span>{{ w.created_at }} — <b>{{ w.amount|floatformat:2 }} ₽</b></span>
                <span class="badge {% if w.status == 'approved' %}text-bg-success{% elif w.status == 'pending' %}text-bg-warning{% else %}text-bg-danger{% endif %}">{{ w.status }}</span>
              </li>
            {% endfor %}
          </ul>
          {% endif %}
        </div>
      </div>
    </div>

    <!-- Pending -->
    <div class="col-12 col-lg-8">
      <div class="card shadow-sm h-100">
        <div class="card-body">
          <h5 class="card-title">⏳ Ожидающие брони</h5>
          {% if pending %}
            <div class="table-responsive">
              <table class="table table-sm align-middle">
                <thead><tr><th>#</th><th>Клиент</th><th>Услуга</th><th>Дата</th><th>Время</th><th>Часов</th><th>Сумма</th><th>Оплата</th><th></th></tr></thead>
                <tbody>
                  {% for b in pending %}
                    <tr>
                      <td>{{ b.id }}</td>
                      <td>{{ b.user }}</td>
                      <td>{{ b.board }}</td>
                      <td>{{ b.date }}</td>
                      <td>{% if b.start_time is not None %}{{ b.start_time|default:0 }}:{{ b.start_minute|default:0|stringformat:"02d" }}{% else %}—{% endif %}</td>
                      <td>{{ b.duration }}</td>
                      <td>{{ b.amount|floatformat:0 }} ₽</td>
                      <td><span class="badge {% if b.payment_status == 'paid' %}text-bg-success{% elif b.payment_status == 'pending' %}text-bg-warning{% else %}text-bg-secondary{% endif %}">{{ b.payment_status|default:"unpaid" }}</span></td>
                      <td class="text-nowrap">
                        <form method="post" action="/partner/{{ tg_id }}/confirm/{{ b.id }}/" class="inline">{% csrf_token %}
                          <button class="btn btn-success btn-sm">Подтвердить</button>
                        </form>
                        <form method="post" action="/partner/{{ tg_id }}/cancel/{{ b.id }}/" class="inline">{% csrf_token %}
                          <button class="btn btn-outline-danger btn-sm">Отменить</button>
                        </form>
                      </td>
                    </tr>
                  {% endfor %}
                </tbody>
              </table>
            </div>
          {% else %}
            <div class="text-muted">Нет ожидающих.</div>
          {% endif %}
        </div>
      </div>
    </div>

    <!-- Orders -->
    <div class="col-12">
      <div class="card shadow-sm">
        <div class="card-body">
          <h5 class="card-title">📦 Последние заказы</h5>
          {% if orders %}
            <div class="table-responsive">
              <table class="table table-sm">
                <thead><tr><th>#</th><th>Клиент</th><th>Услуга</th><th>Дата</th><th>Время</th><th>Часов</th><th>Сумма</th><th>Статус</th><th>Оплата</th><th></th></tr></thead>
                <tbody>
                  {% for o in orders %}
                  <tr>
                    <td>{{ o.id }}</td><td>{{ o.user }}</td><td>{{ o.board }}</td>
                    <td>{{ o.date }}</td>
                    <td>{% if o.start_time is not None %}{{ o.start_time|default:0 }}:{{ o.start_minute|default:0|stringformat:"02d" }}{% else %}—{% endif %}</td>
                    <td>{{ o.duration }}</td>
                    <td>{{ o.amount|floatformat:0 }} ₽</td>
                    <td>{{ o.status }}</td>
                    <td><span class="badge {% if o.payment_status == 'paid' %}text-bg-success{% elif o.payment_status == 'pending' %}text-bg-warning{% else %}text-bg-secondary{% endif %}">{{ o.payment_status|default:"unpaid" }}</span></td>
                    <td class="text-nowrap">
                      {% if o.status == 'active' %}
                        <form method="post" action="/partner/{{ tg_id }}/complete/{{ o.id }}/" class="inline">{% csrf_token %}
                          <button class="btn btn-outline-primary btn-sm">Завершить</button>
                        </form>
                      {% endif %}
                    </td>
                  </tr>
                  {% endfor %}
                </tbody>
              </table>
            </div>
          {% else %}<div class="text-muted">Пока пусто.</div>{% endif %}
        </div>
      </div>
    </div>

    <!-- Locations -->
    <div class="col-12 col-lg-6">
      <div class="card shadow-sm h-100">
        <div class="card-body">
          <h5 class="card-title">📍 Локации</h5>
          {% if locations %}
            <ul class="list-group list-group-flush">
              {% for l in locations %}
                <li class="list-group-item d-flex justify-content-between align-items-center">
                  <span>{{ l.name }}</span>
                  <span class="small text-muted">
                    {{ l.lat }}, {{ l.lon }} · {% if l.kind == 'handover' %}выдача/сдача{% else %}точка катания{% endif %}
                  </span>
                </li>
              {% endfor %}
            </ul>
          {% else %}<div class="text-muted">Нет локаций</div>{% endif %}
          <hr>
          <form method="post" action="/partner/{{ tg_id }}/add-location/">
            {% csrf_token %}
            <div class="row g-2">
              <div class="col-12"><input name="name" required class="form-control" placeholder="Название локации"></div>
              <div class="col-6"><input name="lat" step="0.000001" class="form-control" placeholder="Широта (кликните по карте)"></div>
              <div class="col-6"><input name="lon" step="0.000001" class="form-control" placeholder="Долгота (кликните по карте)"></div>
              <div class="col-12">
                <select name="kind" class="form-select">
                  <option value="spot">Точка катания</option>
                  <option value="handover">Выдача/сдача</option>
                </select>
              </div>
              <div class="col-12">
                <div id="pickmap"></div>
                <div class="form-text">Кликните по карте, чтобы подставить координаты. Маркер можно перетаскивать.</div>
              </div>
              <div class="col-12 d-grid"><button class="btn btn-outline-secondary" type="submit">Добавить</button></div>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Boards (почас) -->
    <div class="col-12 col-lg-6">
      <div class="card shadow-sm h-100">
        <div class="card-body">
          <h5 class="card-title">📋 Доски (почас)</h5>
          {% if boards %}
            <div class="table-responsive">
              <table class="table table-sm">
                <thead><tr><th>Название</th><th>Локация</th><th>Цена</th><th>Всего</th></tr></thead>
                <tbody>
                  {% for b in boards %}
                    <tr><td>{{ b.name }}</td><td>{{ b.location }}</td><td>{{ b.price|floatformat:0 }} ₽/ч</td><td>{{ b.total }}</td></tr>
                  {% endfor %}
                </tbody>
              </table>
            </div>
          {% else %}<div class="text-muted">Досок ещё нет</div>{% endif %}
          <hr>
          <form method="post" action="/partner/{{ tg_id }}/add-board/">
            {% csrf_token %}
            <div class="row g-2">
              <div class="col-12"><input name="name" required class="form-control" placeholder="Название доски"></div>
              <div class="col-6"><input name="price" type="number" required step="0.01" class="form-control" placeholder="Цена ₽/ч"></div>
              <div class="col-6"><input name="qty" type="number" required min="1" class="form-control" placeholder="Количество (всего)"></div>
              <div class="col-12">
                <select class="form-select" name="location_id" required>
                  <option value="" selected disabled>Локация…</option>
                  {% for l in locations %}
                    <option value="{{ l.id }}">{{ l.name }}</option>
                  {% endfor %}
                </select>
              </div>
              <div class="col-12 d-grid"><button class="btn btn-outline-secondary" type="submit">Добавить доску</button></div>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- DAILY (P2P объявления) -->
    <div class="col-12">
      <div class="card shadow-sm">
        <div class="card-body">
          <div class="d-flex justify-content-between align-items-center">
            <h5 class="card-title m-0">🛍️ Объявления (суточная аренда)</h5>
            <a class="btn btn-outline-dark btn-sm" href="/owner/{{ partner_id }}/">Открыть витрину</a>
          </div>
          {% if daily_boards %}
            <div class="table-responsive">
              <table class="table table-sm">
                <thead><tr><th>#</th><th>Название</th><th>Цена/сутки</th><th>Адрес</th><th>Доступно</th><th>Активно</th></tr></thead>
                <tbody>
                  {% for d in daily_boards %}
                    <tr><td>{{ d.id }}</td><td>{{ d.name }}</td><td>{{ d.daily_price|floatformat:0 }} ₽</td><td>{{ d.address|default:"—" }}</td><td>{{ d.available_quantity }}</td><td>{{ d.is_active }}</td></tr>
                  {% endfor %}
                </tbody>
              </table>
            </div>
          {% else %}<div class="text-muted">Объявлений нет</div>{% endif %}
          <hr>
          <form method="post" action="/partner/{{ tg_id }}/add-daily/">
            {% csrf_token %}
            <div class="row g-2">
              <div class="col-md-5"><input name="name" class="form-control" placeholder="Название" required></div>
              <div class="col-md-3"><input name="price" type="number" class="form-control" step="0.01" placeholder="Цена/сутки" required></div>
              <div class="col-md-2"><input name="qty" type="number" class="form-control" min="1" value="1" placeholder="Кол-во" required></div>
              <div class="col-md-2"><input name="address" class="form-control" placeholder="Адрес"></div>
              <div class="col-12 d-grid"><button class="btn btn-outline-secondary">Добавить объявление</button></div>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Купоны -->
    <div class="col-12">
      <div class="card shadow-sm">
        <div class="card-body">
          <h5 class="card-title">🏷️ Купоны</h5>
          {% if coupons %}
          <div class="table-responsive">
            <table class="table table-sm"><thead><tr><th>Код</th><th>Тип</th><th>Значение</th><th>Использовано</th><th>Лимит</th><th>Период</th><th>Активен</th></tr></thead>
            <tbody>
              {% for c in coupons %}
                <tr><td>{{ c.code }}</td><td>{{ c.type }}</td><td>{{ c.value }}</td><td>{{ c.used }}</td><td>{{ c.max_uses }}</td><td>{{ c.valid_from }} → {{ c.valid_to }}</td><td>{{ c.active }}</td></tr>
              {% endfor %}
            </tbody></table>
          </div>
          {% else %}<div class="text-muted">Купонов нет.</div>{% endif %}
          <hr>
          <form class="row g-2" method="post" action="/partner/{{ tg_id }}/add-coupon/">
            {% csrf_token %}
            <div class="col-md-3"><input name="code" class="form-control" placeholder="Код" required></div>
            <div class="col-md-2">
              <select class="form-select" name="ctype">
                <option value="percent">%</option>
                <option value="fixed">₽</option>
              </select>
            </div>
            <div class="col-md-2"><input name="value" type="number" step="0.01" class="form-control" placeholder="Значение" required></div>
            <div class="col-md-2"><input name="max_uses" type="number" class="form-control" placeholder="Лимит"></div>
            <div class="col-md-3"><input name="period" class="form-control" placeholder="YYYY-MM-DD..YYYY-MM-DD"></div>
            <div class="col-12 d-grid"><button class="btn btn-outline-secondary">Создать купон</button></div>
          </form>
        </div>
      </div>
    </div>

  </div>
  {% else %}
    <div class="alert alert-warning">Этот Telegram ID не найден в таблице партнёров.
      <a href="/partner/{{ tg_id }}/become/" class="ms-2">Стать партнёром</a>
    </div>
  {% endif %}

  {% if partner_id %}
  <script src="{{ ymaps_api }}"></script>
  <script>
    // Пикер координат для добавления локаций
    ymaps.ready(function() {
      const latInput = document.querySelector('input[name="lat"]');
      const lonInput = document.querySelector('input[name="lon"]');

      const startLat = {{ default_lat }};
      const startLon = {{ default_lon }};
      const map = new ymaps.Map('pickmap', {
        center:[startLat, startLon], zoom: {{ default_zoom }},
        controls:['zoomControl','geolocationControl','searchControl']
      });

      let placemark = null;
      function setPoint(coords) {
        latInput.value = coords[0].toFixed(6);
        lonInput.value = coords[1].toFixed(6);
        if (!placemark) {
          placemark = new ymaps.Placemark(coords, {balloonContent:'Новая локация'}, {draggable:true, preset:'islands#blueDotIcon'});
          placemark.events.add('dragend', function(){
            const c = placemark.geometry.getCoordinates(); setPoint(c);
          });
          map.geoObjects.add(placemark);
        } else {
          placemark.geometry.setCoordinates(coords);
        }
      }
      map.events.add('click', function(e){ setPoint(e.get('coords')); });

      // существующие точки
      const existing = JSON.parse('{{ partner_markers_json|escapejs }}');
      existing.forEach(m => {
        const preset = (m.kind === 'handover') ? 'islands#orangeIcon' : 'islands#blueIcon';
        const pm = new ymaps.Placemark([m.lat, m.lon], {balloonContent:`<b>${m.name}</b>`}, {preset});
        map.geoObjects.add(pm);
      });
      if (existing.length) {
        const b = map.geoObjects.getBounds();
        if (b) map.setBounds(b, {checkZoomRange:true, zoomMargin:20});
      }
    });
  </script>
  {% endif %}
{% endblock %}
''',

                    # EMPLOYEE
                    "employee.html": r'''
{% extends "base.html" %}
{% block title %}Кабинет сотрудника{% endblock %}
{% block content %}
  <div class="d-flex align-items-center gap-3 mb-3">
    <h3 class="m-0">🧑‍🔧 Сотрудник партнёра</h3>
    <span class="badge text-bg-secondary">tg_id: {{ tg_id }}</span>
    <a class="btn btn-outline-dark btn-sm" href="/m/{{ tg_id }}/">Мобильный экран</a>
  </div>
  {% if partners %}
    <div class="alert alert-secondary py-2">Привязан к партнёрам: {{ partners|join:", " }}</div>
  {% endif %}
  <div class="card shadow-sm">
    <div class="card-body">
      <h5 class="card-title">Сегодняшние брони</h5>
      {% if bookings %}
      <div class="table-responsive">
        <table class="table table-sm align-middle">
          <thead><tr><th>#</th><th>Клиент</th><th>Услуга</th><th>Дата</th><th>Время</th><th>Часов</th><th>Сумма</th><th>Оплата</th><th>Статус</th><th></th></tr></thead>
          <tbody>
            {% for b in bookings %}
              <tr>
                <td>{{ b.id }}</td>
                <td>{{ b.user }}</td>
                <td>{{ b.board }}</td>
                <td>{{ b.date }}</td>
                <td>{% if b.start_time is not None %}{{ b.start_time|default:0 }}:{{ b.start_minute|default:0|stringformat:"02d" }}{% else %}—{% endif %}</td>
                <td>{{ b.duration }}</td>
                <td>{{ b.amount|floatformat:0 }} ₽</td>
                <td><span class="badge {% if b.payment_status == 'paid' %}text-bg-success{% elif b.payment_status == 'pending' %}text-bg-warning{% else %}text-bg-secondary{% endif %}">{{ b.payment_status|default:"unpaid" }}</span></td>
                <td>{{ b.status }}</td>
                <td class="text-nowrap">
                  {% if b.status in 'waiting_partner waiting_card waiting_cash' %}
                    <form method="post" action="/employee/{{ tg_id }}/confirm/{{ b.id }}/" class="inline">{% csrf_token %}<button class="btn btn-success btn-sm">Подтвердить</button></form>
                    <form method="post" action="/employee/{{ tg_id }}/cancel/{{ b.id }}/" class="inline">{% csrf_token %}<button class="btn btn-outline-danger btn-sm">Отменить</button></form>
                  {% elif b.status == 'active' %}
                    <form method="post" action="/employee/{{ tg_id }}/complete/{{ b.id }}/" class="inline">{% csrf_token %}<button class="btn btn-outline-primary btn-sm">Завершить</button></form>
                  {% endif %}
                </td>
              </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
      {% else %}
        <div class="text-muted">Нет броней на сегодня.</div>
      {% endif %}
    </div>
  </div>
{% endblock %}
''',

                    # Мобильный экран сотрудника (без изменений действий — уже POST)
                    "mobile_employee.html": r'''
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Выдача — {{ tg_id }}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <style> body{padding:14px} .card{border-radius:14px} .photo{width:100%;border:1px dashed #ccc;padding:8px;border-radius:10px}</style>
</head>
<body>
  <div class="d-flex justify-content-between align-items-center mb-2">
    <h5 class="m-0">🧑‍🔧 Выдача · {{ today }}</h5>
    <a class="btn btn-sm btn-outline-dark" href="/employee/{{ tg_id }}/">Кабинет</a>
  </div>
  {% if bookings %}
    {% for b in bookings %}
    <div class="card mb-3">
      <div class="card-body">
        <div class="d-flex justify-content-between mb-1">
          <div><b>#{{ b.id }}</b> · {{ b.board }}</div>
          <span class="badge {% if b.payment_status == 'paid' %}text-bg-success{% elif b.payment_status == 'pending' %}text-bg-warning{% else %}text-bg-secondary{% endif %}">{{ b.payment_status|default:"unpaid" }}</span>
        </div>
        <div class="small text-muted">{{ b.date }} · {% if b.start_time is not None %}{{ b.start_time|default:0 }}:{{ b.start_minute|default:0|stringformat:"02d" }}{% else %}—{% endif %} · {{ b.duration }}ч · {{ b.amount|floatformat:0 }} ₽</div>
        <div class="mt-2 d-flex gap-2">
          <form method="post" action="/m/{{ tg_id }}/booking/{{ b.id }}/start/"><button class="btn btn-success btn-sm" {% if b.started_at %}disabled{% endif %}>Старт</button></form>
          <form method="post" action="/m/{{ tg_id }}/booking/{{ b.id }}/stop/"><button class="btn btn-outline-primary btn-sm" {% if not b.started_at or b.ended_at %}disabled{% endif %}>Стоп</button></form>
          <a class="btn btn-outline-secondary btn-sm" href="/m/{{ tg_id }}/act/{{ b.id }}/" target="_blank">Акт</a>
        </div>
        <hr>
        <div class="row g-2">
          <div class="col-6">
            <form method="post" action="/m/{{ tg_id }}/photo/{{ b.id }}/" enctype="multipart/form-data">
              <input type="hidden" name="ptype" value="before">
              <div class="small">Фото ДО</div>
              <input class="form-control form-control-sm" name="photo" type="file" accept="image/*" capture="environment">
              <button class="btn btn-outline-dark btn-sm mt-1">Загрузить</button>
            </form>
          </div>
          <div class="col-6">
            <form method="post" action="/m/{{ tg_id }}/photo/{{ b.id }}/" enctype="multipart/form-data">
              <input type="hidden" name="ptype" value="after">
              <div class="small">Фото ПОСЛЕ</div>
              <input class="form-control form-control-sm" name="photo" type="file" accept="image/*" capture="environment">
              <button class="btn btn-outline-dark btn-sm mt-1">Загрузить</button>
            </form>
          </div>
        </div>
        {% if b.photos %}
        <div class="mt-2">
          {% for ph in b.photos %}
            <div class="small">{{ ph.type }}: <a href="{{ ph.url }}" target="_blank">смотреть</a></div>
          {% endfor %}
        </div>
        {% endif %}
      </div>
    </div>
    {% endfor %}
  {% else %}
    <div class="text-muted">На сегодня задач нет.</div>
  {% endif %}
</body>
</html>
''',

                    # Витрина владельца
                    "owner.html": r'''
{% extends "base.html" %}
{% block title %}Витрина владельца #{{ pid }}{% endblock %}
{% block content %}
  <div class="d-flex align-items-center justify-content-between mb-3">
    <div>
      <h3 class="m-0">👤 Владелец #{{ pid }} — {{ name }}</h3>
      <div class="small text-muted">Рейтинг: {{ rating|floatformat:1 }} ★ ({{ reviews_count }} отзывов)</div>
      <div class="small text-muted">Страховка залога: {{ deposit_insurance }}</div>
    </div>
    <a class="btn btn-outline-secondary btn-sm" href="/#mapwrap">← На карту</a>
  </div>

  <div class="row g-4">
    <div class="col-lg-6">
      <div class="card shadow-sm h-100">
        <div class="card-body">
          <h5 class="card-title">📋 Почасовые предложения</h5>
          {% if boards %}
          <ul class="list-group list-group-flush">
            {% for b in boards %}
              <li class="list-group-item d-flex justify-content-between">
                <span>{{ b.name }} · {{ b.location }}</span>
                <span>{{ b.price|floatformat:0 }} ₽/ч · всего {{ b.total }}</span>
              </li>
            {% endfor %}
          </ul>
          {% else %}<div class="text-muted">Нет предложений.</div>{% endif %}
        </div>
      </div>
    </div>

    <div class="col-lg-6">
      <div class="card shadow-sm h-100">
        <div class="card-body">
          <h5 class="card-title">🛍️ Объявления (сутки)</h5>
          {% if daily %}
            <div class="table-responsive">
              <table class="table table-sm"><thead><tr><th>Название</th><th>Цена/сутки</th><th>Адрес</th><th>Доступно</th></tr></thead>
              <tbody>
                {% for d in daily %}
                  <tr><td>{{ d.name }}</td><td>{{ d.daily_price|floatformat:0 }} ₽</td><td>{{ d.address|default:"—" }}</td><td>{{ d.available_quantity }}</td></tr>
                {% endfor %}
              </tbody></table>
            </div>
          {% else %}<div class="text-muted">Пока пусто.</div>{% endif %}
        </div>
      </div>
    </div>
  </div>
{% endblock %}
''',

                    # ADMIN
                    "admin.html": r'''
{% extends "base.html" %}
{% block title %}Админка{% endblock %}
{% block content %}
  <div class="d-flex justify-content-between align-items-center mb-3">
    <h3 class="m-0">🔧 Админка</h3>
    <div><a class="btn btn-sm btn-outline-dark" href="/admin/{{ tg_id }}/finance/">Финансы</a></div>
  </div>

  <div class="row g-3">
    <div class="col-md-4"><div class="tile"><div class="muted">Партнёры</div><div class="stat-lg">{{ stat.partners }}</div></div></div>
    <div class="col-md-4"><div class="tile"><div class="muted">Пользователи</div><div class="stat-lg">{{ stat.users }}</div></div></div>
    <div class="col-md-4"><div class="tile"><div class="muted">Брони (сегодня)</div><div class="stat-lg">{{ stat.today_bookings }}</div></div></div>
  </div>

  <div class="card shadow-sm mt-4">
    <div class="card-body">
      <h5 class="card-title">Последние брони</h5>
      <div class="table-responsive">
        <table class="table table-sm align-middle">
          <thead><tr><th>#</th><th>Польз.</th><th>Услуга</th><th>Дата</th><th>Время</th><th>Часов</th><th>Сумма</th><th>Статус</th><th>Оплата</th><th></th></tr></thead>
          <tbody>
            {% for b in bookings %}
              <tr>
                <td>{{ b.id }}</td>
                <td>{{ b.user }}</td>
                <td>{{ b.board }}</td>
                <td>{{ b.date }}</td>
                <td>{% if b.start_time is not None %}{{ b.start_time|default:0 }}:{{ b.start_minute|default:0|stringformat:"02d" }}{% else %}—{% endif %}</td>
                <td>{{ b.duration }}</td>
                <td>{{ b.amount|floatformat:0 }} ₽</td>
                <td>{{ b.status }}</td>
                <td><span class="badge {% if b.payment_status == 'paid' %}text-bg-success{% elif b.payment_status == 'pending' %}text-bg-warning{% else %}text-bg-secondary{% endif %}">{{ b.payment_status|default:'unpaid' }}</span></td>
                <td class="text-nowrap">
                  <form method="post" action="/admin/{{ tg_id }}/booking/{{ b.id }}/activate/" class="inline">{% csrf_token %}<button class="btn btn-sm btn-outline-primary">Актив</button></form>
                  <form method="post" action="/admin/{{ tg_id }}/booking/{{ b.id }}/complete/" class="inline">{% csrf_token %}<button class="btn btn-sm btn-outline-success">Завершить</button></form>
                  <form method="post" action="/admin/{{ tg_id }}/booking/{{ b.id }}/cancel/" class="inline">{% csrf_token %}<button class="btn btn-sm btn-outline-danger">Отмена</button></form>
                </td>
              </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </div>
  </div>
{% endblock %}
''',

                    "admin_finance.html": r'''
{% extends "base.html" %}
{% block title %}Финансы — админ{% endblock %}
{% block content %}
  <div class="d-flex justify-content-between align-items-center mb-3">
    <h3 class="m-0">💸 Финансы</h3>
    <a class="btn btn-outline-secondary btn-sm" href="/admin/{{ tg_id }}/">← Админка</a>
  </div>

  <div class="row g-3">
    <div class="col-md-3"><div class="tile"><div class="muted">Выручка (оплач.)</div><div class="stat-lg">{{ money.revenue|floatformat:0 }} ₽</div></div></div>
    <div class="col-md-3"><div class="tile"><div class="muted">Расходы</div><div class="stat-lg">{{ money.expenses|floatformat:0 }} ₽</div></div></div>
    <div class="col-md-3"><div class="tile"><div class="muted">Прибыль</div><div class="stat-lg">{{ money.profit|floatformat:0 }} ₽</div></div></div>
    <div class="col-md-3"><div class="tile"><div class="muted">Комиссия платформы</div><div class="stat-lg">{{ commission|floatformat:1 }} %</div></div></div>
  </div>

  <div class="row g-4 mt-1">
    <div class="col-lg-6">
      <div class="card shadow-sm">
        <div class="card-body">
          <h5 class="card-title">Заявки на вывод</h5>
          <div class="table-responsive">
            <table class="table table-sm">
              <thead><tr><th>#</th><th>Партнёр</th><th>Сумма</th><th>Статус</th><th>Дата</th><th></th></tr></thead>
              <tbody>
                {% for w in withdraws %}
                  <tr>
                    <td>{{ w.id }}</td><td>{{ w.partner_id }}</td><td>{{ w.amount|floatformat:0 }} ₽</td>
                    <td>{{ w.status }}</td><td>{{ w.created_at }}</td>
                    <td class="text-nowrap">
                      {% if w.status == 'pending' %}
                        <form method="post" action="/admin/{{ tg_id }}/withdraw/{{ w.id }}/approve/" class="inline">{% csrf_token %}<button class="btn btn-sm btn-success">Подтвердить</button></form>
                        <form method="post" action="/admin/{{ tg_id }}/withdraw/{{ w.id }}/reject/" class="inline">{% csrf_token %}<button class="btn btn-sm btn-outline-danger">Отклонить</button></form>
                      {% endif %}
                    </td>
                  </tr>
                {% endfor %}
              </tbody>
            </table>
          </div>
        </div>
      </div>
      <div class="card shadow-sm mt-3">
        <div class="card-body">
          <h5 class="card-title">Экспорт</h5>
          <a class="btn btn-outline-dark btn-sm" href="/admin/{{ tg_id }}/finance/export/bookings/">Экспорт броней (CSV)</a>
          <a class="btn btn-outline-dark btn-sm ms-2" href="/admin/{{ tg_id }}/finance/export/payments/">Экспорт платежей (CSV)</a>
        </div>
      </div>
    </div>

    <div class="col-lg-6">
      <div class="card shadow-sm">
        <div class="card-body">
          <h5 class="card-title">Расходы</h5>
          <form class="row g-2" method="post" action="/admin/{{ tg_id }}/finance/add-expense/">
            {% csrf_token %}
            <div class="col-4"><input name="date" class="form-control" value="{{ today }}" required></div>
            <div class="col-3"><input name="amount" type="number" step="0.01" class="form-control" placeholder="Сумма" required></div>
            <div class="col-5"><input name="description" class="form-control" placeholder="Описание"></div>
            <div class="col-12 d-grid"><button class="btn btn-outline-secondary btn-sm">Добавить</button></div>
          </form>
          <hr>
          <div class="table-responsive">
            <table class="table table-sm"><thead><tr><th>#</th><th>Дата</th><th>Сумма</th><th>Описание</th><th></th></tr></thead>
            <tbody>
              {% for e in expenses %}
                <tr><td>{{ e.id }}</td><td>{{ e.date }}</td><td>{{ e.amount|floatformat:0 }}</td><td>{{ e.description }}</td>
                  <td>
                    <form method="post" action="/admin/{{ tg_id }}/finance/expense/{{ e.id }}/delete/" class="inline">{% csrf_token %}
                      <button class="btn btn-sm btn-outline-danger">Удалить</button>
                    </form>
                  </td></tr>
              {% endfor %}
            </tbody></table>
          </div>
        </div>
      </div>
      <div class="card shadow-sm mt-3">
        <div class="card-body">
          <h5 class="card-title">Комиссия платформы</h5>
          <form class="row g-2" method="post" action="/admin/{{ tg_id }}/finance/set-commission/">
            {% csrf_token %}
            <div class="col-8"><input name="value" type="number" step="0.1" class="form-control" value="{{ commission|floatformat:1 }}"></div>
            <div class="col-4 d-grid"><button class="btn btn-outline-primary btn-sm">Сохранить</button></div>
          </form>
        </div>
      </div>
    </div>
  </div>
{% endblock %}
''',

                    "admin_finance_partner.html": r'''
{% extends "base.html" %}
{% block title %}Финансы партнёра #{{ pid }}{% endblock %}
{% block content %}
  <div class="d-flex justify-content-between align-items-center mb-3">
    <h3 class="m-0">Партнёр #{{ pid }}</h3>
    <a class="btn btn-outline-secondary btn-sm" href="/admin/{{ tg_id }}/finance/">← Финансы</a>
  </div>

  <div class="row g-3">
    <div class="col-md-4"><div class="tile"><div class="muted">Баланс</div><div class="stat-lg">{{ balance|floatformat:0 }} ₽</div></div></div>
    <div class="col-md-4"><div class="tile"><div class="muted">Комиссия</div><div class="stat-lg">{{ commission|floatformat:1 }} %</div></div></div>
  </div>

  <div class="card shadow-sm mt-3">
    <div class="card-body">
      <h5 class="card-title">Установить комиссию</h5>
      <form class="row g-2" method="post" action="/admin/{{ tg_id }}/finance/partner/{{ pid }}/set-commission/">
        {% csrf_token %}
        <div class="col-8"><input name="value" type="number" step="0.1" class="form-control" value="{{ commission|floatformat:1 }}"></div>
        <div class="col-4 d-grid"><button class="btn btn-outline-primary btn-sm">Сохранить</button></div>
      </form>
    </div>
  </div>
{% endblock %}
''',
                })]
            }
        }],
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": DEFAULT_DB_PATH,
                "OPTIONS": {"timeout": 20},
            }
        },
        STATIC_URL="/static/",
    )

import django
django.setup()

# -----------------------------
# SQL helpers
# -----------------------------
def _adapt_sql(sql: str) -> str:
    return sql

def q_all(sql: str, params=()):
    with connections["default"].cursor() as c:
        c.execute(_adapt_sql(sql), params)
        return [tuple(row) for row in c.fetchall()]

def q_one(sql: str, params=()):
    with connections["default"].cursor() as c:
        c.execute(_adapt_sql(sql), params)
        return c.fetchone()

def q_exec(sql: str, params=()):
    with connections["default"].cursor() as c:
        c.execute(_adapt_sql(sql), params)

# -----------------------------
# Schema bootstrap / migrations
# -----------------------------
SCHEMA_SQL = [
    # partners/users/admins
    """
    CREATE TABLE IF NOT EXISTS partners (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL DEFAULT 'Партнёр',
        contact_email TEXT,
        telegram_id INTEGER UNIQUE,
        is_active INTEGER DEFAULT 1,
        is_approved INTEGER DEFAULT 0,
        commission_percent REAL DEFAULT 10,
        logo TEXT,
        url TEXT,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        phone TEXT,
        is_banned INTEGER DEFAULT 0,
        reg_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        level INTEGER DEFAULT 1 CHECK(level BETWEEN 1 AND 3),
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    # locations
    """
    CREATE TABLE IF NOT EXISTS locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        address TEXT,
        latitude REAL,
        longitude REAL,
        kind TEXT DEFAULT 'spot' CHECK(kind IN ('spot','handover')),
        is_active INTEGER DEFAULT 1,
        partner_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(partner_id) REFERENCES partners(id) ON DELETE SET NULL
    )
    """,
    # boards
    """
    CREATE TABLE IF NOT EXISTS boards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT DEFAULT '',
        total INTEGER NOT NULL CHECK(total > 0),
        quantity INTEGER NOT NULL DEFAULT 0,
        price REAL NOT NULL DEFAULT 1000,
        is_active INTEGER DEFAULT 1,
        partner_id INTEGER,
        location_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(partner_id) REFERENCES partners(id) ON DELETE SET NULL,
        FOREIGN KEY(location_id) REFERENCES locations(id) ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS board_images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        board_id INTEGER NOT NULL,
        file_id TEXT NOT NULL,
        FOREIGN KEY(board_id) REFERENCES boards(id) ON DELETE CASCADE
    )
    """,
    # daily_boards
    """
    CREATE TABLE IF NOT EXISTS daily_boards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT DEFAULT '',
        daily_price REAL NOT NULL DEFAULT 1000,
        address TEXT,
        available_quantity INTEGER NOT NULL DEFAULT 1,
        is_active INTEGER DEFAULT 1,
        partner_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(partner_id) REFERENCES partners(id) ON DELETE SET NULL
    )
    """,
    # bookings
    """
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        board_id INTEGER,
        board_name TEXT,
        date DATE NOT NULL,
        start_time INTEGER,
        start_minute INTEGER,
        duration INTEGER NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        amount REAL NOT NULL DEFAULT 0,
        status TEXT DEFAULT 'waiting_partner'
            CHECK(status IN ('waiting_partner','active','canceled','completed',
                             'waiting_card','waiting_cash','waiting_daily')),
        payment_method TEXT,
        payment_status TEXT DEFAULT 'unpaid'
            CHECK(payment_status IN ('unpaid','pending','paid','failed','refunded')),
        started_at TIMESTAMP,
        ended_at TIMESTAMP,
        daily_board_id INTEGER,
        coupon_code TEXT,
        partner_credited INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(board_id) REFERENCES boards(id) ON DELETE RESTRICT,
        FOREIGN KEY(daily_board_id) REFERENCES daily_boards(id) ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS partner_wallet_ops (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        partner_id INTEGER NOT NULL,
        booking_id INTEGER,
        type TEXT NOT NULL CHECK(type IN ('credit','debit')),
        amount REAL NOT NULL,
        src TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(partner_id) REFERENCES partners(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id TEXT NOT NULL,
        partner_id INTEGER NOT NULL,
        commission_percent REAL NOT NULL CHECK(commission_percent BETWEEN 0 AND 100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(partner_id) REFERENCES partners(id) ON DELETE CASCADE,
        UNIQUE(telegram_id, partner_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS employee_wallet_ops (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_telegram_id TEXT NOT NULL,
        booking_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        src TEXT DEFAULT 'booking_commission',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(booking_id) REFERENCES bookings(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS partner_withdraw_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        partner_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        status TEXT DEFAULT 'pending'
            CHECK(status IN ('pending','approved','rejected')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(partner_id) REFERENCES partners(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        amount REAL NOT NULL,
        description TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id INTEGER NOT NULL,
        provider TEXT NOT NULL,
        provider_payment_id TEXT,
        amount REAL NOT NULL,
        currency TEXT DEFAULT 'RUB',
        status TEXT NOT NULL DEFAULT 'pending'
            CHECK(status IN ('pending','succeeded','canceled','refunded','failed')),
        confirmation_url TEXT,
        payload TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(booking_id) REFERENCES bookings(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS coupons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        type TEXT NOT NULL CHECK(type IN ('percent','fixed')),
        value REAL NOT NULL,
        max_uses INTEGER,
        used INTEGER DEFAULT 0,
        valid_from DATE,
        valid_to DATE,
        partner_id INTEGER,
        active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS referrals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inviter_user_id INTEGER NOT NULL,
        invited_user_id INTEGER UNIQUE,
        bonus_amount REAL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ratings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        partner_id INTEGER NOT NULL,
        user_id INTEGER,
        value REAL NOT NULL CHECK(value BETWEEN 1 AND 5),
        comment TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS booking_photos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id INTEGER NOT NULL,
        type TEXT CHECK(type IN ('before','after')),
        url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(booking_id) REFERENCES bookings(id) ON DELETE CASCADE
    )
    """,
]

INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_boards_partner ON boards(partner_id)",
    "CREATE INDEX IF NOT EXISTS idx_boards_location ON boards(location_id)",
    "CREATE INDEX IF NOT EXISTS idx_bookings_board ON bookings(board_id)",
    "CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status)",
    "CREATE INDEX IF NOT EXISTS idx_bookings_date ON bookings(date)",
    "CREATE INDEX IF NOT EXISTS idx_payments_booking ON payments(booking_id)",
    "CREATE INDEX IF NOT EXISTS idx_coupons_code ON coupons(code)",
    "CREATE INDEX IF NOT EXISTS idx_employees_partner ON employees(partner_id)",
    "CREATE INDEX IF NOT EXISTS idx_employee_ops_emp ON employee_wallet_ops(employee_telegram_id)"
]

def ensure_schema():
    try:
        call_command("migrate", interactive=False, run_syncdb=True, verbosity=0)
    except Exception:
        pass
    with transaction.atomic():
        for sql in SCHEMA_SQL:
            q_exec(sql)

        # Добавим недостающие колонки для обратной совместимости
        def table_cols(name):
            return {r[1]: r for r in q_all(f"PRAGMA table_info({name})")}
        # locations.kind
        if "kind" not in table_cols("locations"):
            q_exec("ALTER TABLE locations ADD COLUMN kind TEXT DEFAULT 'spot'")
        # bookings extras
        bcols = table_cols("bookings")
        if "payment_status" not in bcols:
            q_exec("ALTER TABLE bookings ADD COLUMN payment_status TEXT DEFAULT 'unpaid'")
        if "started_at" not in bcols:
            q_exec("ALTER TABLE bookings ADD COLUMN started_at TIMESTAMP")
        if "ended_at" not in bcols:
            q_exec("ALTER TABLE bookings ADD COLUMN ended_at TIMESTAMP")
        if "daily_board_id" not in bcols:
            q_exec("ALTER TABLE bookings ADD COLUMN daily_board_id INTEGER")
        if "coupon_code" not in bcols:
            q_exec("ALTER TABLE bookings ADD COLUMN coupon_code TEXT")
        if "partner_credited" not in bcols:
            q_exec("ALTER TABLE bookings ADD COLUMN partner_credited INTEGER DEFAULT 0")

        # partner_wallet_ops.booking_id
        pwcols = table_cols("partner_wallet_ops")
        if "booking_id" not in pwcols:
            q_exec("ALTER TABLE partner_wallet_ops ADD COLUMN booking_id INTEGER")

        # payments.confirmation_url
        pcols = table_cols("payments")
        if "confirmation_url" not in pcols:
            q_exec("ALTER TABLE payments ADD COLUMN confirmation_url TEXT")

        # Если вдруг в старой таблице bookings.board_id был NOT NULL — переливаем
        info_b = q_all("PRAGMA table_info(bookings)")
        board_col = next((r for r in info_b if r[1] == "board_id"), None)
        if board_col and board_col[3] == 1:  # notnull
            q_exec("""
                CREATE TABLE IF NOT EXISTS bookings_new(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    board_id INTEGER,
                    board_name TEXT,
                    date DATE NOT NULL,
                    start_time INTEGER,
                    start_minute INTEGER,
                    duration INTEGER NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 1,
                    amount REAL NOT NULL DEFAULT 0,
                    status TEXT DEFAULT 'waiting_partner'
                        CHECK(status IN ('waiting_partner','active','canceled','completed',
                                         'waiting_card','waiting_cash','waiting_daily')),
                    payment_method TEXT,
                    payment_status TEXT DEFAULT 'unpaid'
                        CHECK(payment_status IN ('unpaid','pending','paid','failed','refunded')),
                    started_at TIMESTAMP,
                    ended_at TIMESTAMP,
                    daily_board_id INTEGER,
                    coupon_code TEXT,
                    partner_credited INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            q_exec("""
                INSERT INTO bookings_new
                (id,user_id,board_id,board_name,date,start_time,start_minute,duration,quantity,amount,status,payment_method,payment_status,started_at,ended_at,daily_board_id,coupon_code,partner_credited,created_at)
                SELECT id,user_id,board_id,board_name,date,start_time,start_minute,duration,quantity,amount,status,payment_method,
                       COALESCE(payment_status,'unpaid'),started_at,ended_at,
                       CASE WHEN EXISTS(SELECT 1 FROM pragma_table_info('bookings') WHERE name='daily_board_id') THEN daily_board_id ELSE NULL END,
                       CASE WHEN EXISTS(SELECT 1 FROM pragma_table_info('bookings') WHERE name='coupon_code') THEN coupon_code ELSE NULL END,
                       0,
                       created_at
                FROM bookings
            """)
            q_exec("DROP TABLE bookings")
            q_exec("ALTER TABLE bookings_new RENAME TO bookings")

        for idx in INDEXES_SQL:
            q_exec(idx)

def ensure_admins_from_env():
    admin_env = os.environ.get("ADMIN_IDS", "")
    for s in [x.strip() for x in admin_env.split(",") if x.strip().isdigit()]:
        uid = int(s)
        if not q_one("SELECT 1 FROM admins WHERE user_id = ?", (uid,)):
            q_exec("INSERT INTO admins(user_id, username, level) VALUES(?, ?, 3)", (uid, None))

# -----------------------------
# Utilities
# -----------------------------
def get_setting(key, default=None):
    row = q_one("SELECT value FROM settings WHERE key = ?", (key,))
    return (row[0] if row else default)

def set_setting(key, value):
    if q_one("SELECT 1 FROM settings WHERE key = ?", (key,)):
        q_exec("UPDATE settings SET value = ?, updated_at = CURRENT_TIMESTAMP WHERE key = ?", (value, key))
    else:
        q_exec("INSERT INTO settings(key, value) VALUES(?, ?)", (key, value))

def platform_commission_percent() -> float:
    try:
        v = get_setting("PLATFORM_COMMISSION_PERCENT", None)
        if v is not None: return float(v)
    except Exception:
        pass
    try:
        return float(os.environ.get("PLATFORM_COMMISSION_PERCENT", "10"))
    except Exception:
        return 10.0

def partner_effective_commission(pid: int) -> float:
    row = q_one("SELECT commission_percent FROM partners WHERE id = ?", (pid,))
    if row and row[0] is not None:
        try: return float(row[0])
        except Exception: pass
    return platform_commission_percent()

def partner_id_by_tg(tg_id: int):
    row = q_one("SELECT id FROM partners WHERE telegram_id = ?", (tg_id,))
    return row[0] if row else None

def partner_balance(partner_id: int) -> float:
    cr = q_one("SELECT COALESCE(SUM(amount),0) FROM partner_wallet_ops WHERE partner_id = ? AND type='credit'", (partner_id,))
    db = q_one("SELECT COALESCE(SUM(amount),0) FROM partner_wallet_ops WHERE partner_id = ? AND type='debit'", (partner_id,))
    return float((cr[0] if cr else 0) - (db[0] if db else 0))

def csrf_token(request):
    return get_token(request)

def _require_self(request, tg_id:int) -> bool:
    try:
        return int(request.session.get("tg_id") or -1) == int(tg_id)
    except Exception:
        return False

def overlapping_quantity(board_id:int, date_iso:str, start_h:int, start_m:int, duration_h:int) -> int:
    s0 = start_h*60 + start_m
    e0 = s0 + duration_h*60
    rows = q_all("""
      SELECT start_time, start_minute, duration, quantity
      FROM bookings
      WHERE board_id = ? AND date = ? AND status IN ('waiting_partner','active','waiting_card','waiting_cash')
    """, (board_id, date_iso))
    used = 0
    for st, mn, dur, q in rows:
        if st is None:
            continue
        s1 = int(st)*60 + int(mn or 0)
        e1 = s1 + int(dur or 0)*60
        if s1 < e0 and e1 > s0:
            used += int(q or 0)
    return used

def check_availability(board_id:int, date_iso:str, start_h:int, start_m:int, duration_h:int, qty:int):
    tot = q_one("SELECT total FROM boards WHERE id = ?", (board_id,))
    total = int((tot[0] if tot else 0) or 0)
    used = overlapping_quantity(board_id, date_iso, start_h, start_m, duration_h)
    avail = max(0, total - used)
    return (qty <= avail, avail, total)

def daily_available(daily_id:int, date_iso:str) -> tuple[bool,int,int]:
    total_row = q_one("SELECT available_quantity FROM daily_boards WHERE id=? AND is_active=1", (daily_id,))
    if not total_row:
        return (False, 0, 0)
    total = int(total_row[0] or 0)
    used = int(q_one("""
      SELECT COALESCE(SUM(quantity),0)
      FROM bookings
      WHERE daily_board_id=? AND date=? AND status IN ('waiting_daily','active','waiting_card','waiting_cash')
    """, (daily_id, date_iso))[0] or 0)
    avail = max(0, total - used)
    return (avail > 0, avail, total)

def dyn_price_for_board(board_id:int, base_price:float, date_iso:str, start_h:int, duration_h:int, qty:int) -> float:
    try: dt = datetime.fromisoformat(date_iso)
    except Exception: dt = datetime.now()
    price = float(base_price)
    weekend = dt.weekday() >= 5
    if weekend and 16 <= start_h <= 21: price *= 1.15
    elif not weekend and 7 <= start_h <= 10: price *= 0.90
    used = overlapping_quantity(board_id, date_iso, start_h, 0, duration_h)
    total = q_one("SELECT total FROM boards WHERE id = ?", (board_id,))[0] or 1
    occ = min(1.0, used / float(total))
    if occ > 0.6: price *= 1.10
    return round(price, 2)

def ymaps_api_url():
    key = os.environ.get("YMAPS_API_KEY")
    base = "https://api-maps.yandex.ru/2.1/?lang=ru_RU"
    return base + (f"&apikey={key}" if key else "")

def _booking_partner_id(booking_id:int):
    row = q_one("""
      SELECT COALESCE(brd.partner_id, db.partner_id)
      FROM bookings b
      LEFT JOIN boards brd ON brd.id=b.board_id
      LEFT JOIN daily_boards db ON db.id=b.daily_board_id
      WHERE b.id=?
    """, (booking_id,))
    return row[0] if row else None

def _credit_partner_if_needed(booking_id:int):
    row = q_one("SELECT amount, payment_status, partner_credited FROM bookings WHERE id=?", (booking_id,))
    if not row: return
    amount, pstat, credited = float(row[0]), row[1], int(row[2] or 0)
    if pstat != 'paid' or credited:  # не начисляем без оплаты и не дублируем
        return
    pid = _booking_partner_id(booking_id)
    if not pid: return
    eff_pct = partner_effective_commission(pid)
    share = round(amount * (1 - eff_pct/100.0), 2)
    q_exec("""
      INSERT INTO partner_wallet_ops(partner_id, booking_id, type, amount, src, created_at)
      VALUES(?, ?, 'credit', ?, 'booking_completed', datetime('now','localtime'))
    """, (pid, booking_id, share))
    q_exec("UPDATE bookings SET partner_credited=1 WHERE id=?", (booking_id,))

def _ensure_logged(request, tg_id:int):
    if not _require_self(request, tg_id):
        return HttpResponse("forbidden", status=403)
    return None

# -----------------------------
# Views — public / core
# -----------------------------
def landing(request):
    ensure_schema()
    ensure_admins_from_env()

    loc_cnt = q_one("SELECT COUNT(*) FROM locations WHERE COALESCE(is_active,1)=1") or (0,)
    brd_cnt = q_one("SELECT COALESCE(SUM(total),0) FROM boards WHERE COALESCE(is_active,1)=1") or (0,)
    today = date.today().isoformat()
    act_cnt = q_one("SELECT COUNT(*) FROM bookings WHERE date = ? AND status='active'", (today,)) or (0,)

    # Агрегируем маркеры по локациям (а не по партнёрам, чтобы не дублировать totals)
    rows = q_all("""
      SELECT p.id, COALESCE(p.name,'Партнёр') as pname,
             COALESCE(l.latitude,0), COALESCE(l.longitude,0), COALESCE(l.kind,'spot'),
             COALESCE(MIN(b.price),0) as min_price, COALESCE(SUM(b.total),0) as total
      FROM partners p
      JOIN locations l ON l.partner_id=p.id AND COALESCE(l.is_active,1)=1
      LEFT JOIN boards b ON b.partner_id=p.id AND COALESCE(b.is_active,1)=1 AND b.location_id=l.id
      WHERE COALESCE(l.latitude,0)<>0 AND COALESCE(l.longitude,0)<>0 AND COALESCE(p.is_active,1)=1
      GROUP BY p.id, pname, l.latitude, l.longitude, l.kind
      ORDER BY p.id DESC
    """)
    markers = []
    for pid, pname, lat, lon, kind, min_price, total in rows:
        markers.append({"partner_id": pid, "name": pname, "lat": float(lat), "lon": float(lon),
                        "kind": kind, "min_price": int(min_price or 0), "total": int(total or 0)})

    locs = [dict(id=r[0], name=r[1]) for r in q_all("SELECT id, name FROM locations WHERE COALESCE(is_active,1)=1 ORDER BY name")]
    boards = [dict(id=r[0], name=r[1], price=r[2], total=r[3], location_id=r[4]) for r in q_all(
        "SELECT id, name, price, total, COALESCE(location_id,0) FROM boards WHERE COALESCE(is_active,1)=1 ORDER BY name"
    )]
    daily_offers = [dict(id=r[0], name=r[1], price=r[2], partner_id=r[3], address=r[4]) for r in q_all(
        "SELECT id, name, daily_price, partner_id, COALESCE(address,'') FROM daily_boards WHERE is_active=1 ORDER BY id DESC"
    )]

    ctx = {
        "stat": {"locations": loc_cnt[0], "boards": int(brd_cnt[0]), "active": act_cnt[0]},
        "locations": locs,
        "boards": boards,
        "daily_offers": daily_offers,
        "today": today,
        "map": {
            "lat": float(os.environ.get("MAP_DEFAULT_LAT", "55.751244")),
            "lon": float(os.environ.get("MAP_DEFAULT_LON", "37.618423")),
            "zoom": int(os.environ.get("MAP_DEFAULT_ZOOM", "11")),
            "markers_json": json.dumps(markers, ensure_ascii=False),
        },
        "ymaps_api": ymaps_api_url(),
    }
    return render(request, "index.html", ctx)

def about(request):
    ensure_schema()
    return render(request, "about.html", {"reviews_channel": os.environ.get("REVIEW_CHANNEL_ID", "@supflot_reviews")})

def signup(request):
    ensure_schema()
    if request.method == "POST":
        tg_id = request.POST.get("tg_id", "").strip()
        username = request.POST.get("username", "").strip() or None
        full_name = request.POST.get("full_name", "").strip() or None
        phone = request.POST.get("phone", "").strip() or None
        if not tg_id.isdigit():
            return HttpResponse("Некорректный tg_id", status=400)
        uid = int(tg_id)
        if not q_one("SELECT 1 FROM users WHERE id = ?", (uid,)):
            q_exec("INSERT INTO users(id, username, full_name, phone) VALUES(?, ?, ?, ?)", (uid, username, full_name, phone))
        request.session["tg_id"] = uid
        return redirect(f"/user/{uid}/")
    return render(request, "auth.html")

def login_view(request):
    ensure_schema()
    if request.method == "POST":
        tg_id = request.POST.get("tg_id", "").strip()
        role = request.POST.get("role", "user")
        if not tg_id.isdigit():
            return HttpResponse("Некорректный tg_id", status=400)
        uid = int(tg_id)
        request.session["tg_id"] = uid
        if role == "partner":
            return redirect(f"/partner/{uid}/")
        if role == "employee":
            return redirect(f"/employee/{uid}/")
        if role == "admin":
            return redirect(f"/admin/{uid}/")
        return redirect(f"/user/{uid}/")
    return render(request, "auth.html")

def logout_view(request):
    request.session.flush()
    return redirect("/")

# -----------------------------
# Booking creation (hourly & daily) + coupons + dynamic price
# -----------------------------
def apply_coupon(code:str|None, amount:float) -> tuple[float, str|None]:
    if not code: return (amount, None)
    row = q_one("""
      SELECT id, type, value, max_uses, used, valid_from, valid_to, active
      FROM coupons WHERE code = ?
    """, (code.strip(),))
    if not row: return (amount, None)
    cid, ctype, val, max_uses, used, vf, vt, active = row
    if not active: return (amount, None)
    today = date.today()
    if vf and today < date.fromisoformat(vf): return (amount, None)
    if vt and today > date.fromisoformat(vt): return (amount, None)
    if max_uses and used >= max_uses: return (amount, None)
    if ctype == "percent":
        amount = max(0.0, amount * (1 - float(val)/100.0))
    else:
        amount = max(0.0, amount - float(val))
    # ВНИМАНИЕ: не увеличиваем used здесь — только после оплаты в вебхуке
    return (round(amount, 2), code.strip())

def book(request):
    ensure_schema()
    if request.method != "POST":
        return redirect("/#book")
    try:
        with transaction.atomic():
            tg_id = int(request.POST.get("tg_id"))
            mode = request.POST.get("mode", "hourly")
            date_iso = request.POST.get("date")
            coupon_code = (request.POST.get("coupon") or "").strip() or None

            if mode == "hourly":
                board_id = int(request.POST.get("board_id"))
                hours = int(request.POST.get("hours"))
                qty = int(request.POST.get("qty"))
                st_h, st_m = [int(x) for x in (request.POST.get("start") or "10:00").split(":")]

                row = q_one("SELECT name, price, total FROM boards WHERE id = ? AND COALESCE(is_active,1)=1", (board_id,))
                if not row: return HttpResponse("Доска не найдена", status=404)
                bname, base_price, total = row

                price = dyn_price_for_board(board_id, base_price, date_iso, st_h, hours, qty)
                amount = float(price) * hours * qty

                ok, avail, total = check_availability(board_id, date_iso, st_h, st_m, hours, qty)
                if not ok:
                    return HttpResponse(f"Недостаточно слотов: доступно {avail} из {total}", status=409)

                amount, applied = apply_coupon(coupon_code, amount)

                q_exec("""
                    INSERT INTO bookings(
                        user_id, board_id, board_name,
                        date, start_time, start_minute,
                        duration, quantity, amount,
                        status, payment_method, payment_status, coupon_code, created_at
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, 'waiting_partner', 'site', 'unpaid', ?, datetime('now','localtime'))
                """, (tg_id, board_id, bname, date_iso, st_h, st_m, hours, qty, amount, applied))

            else:  # daily
                daily_id = int(request.POST.get("daily_board_id"))
                days = int(request.POST.get("days") or 1)
                qty = 1
                row = q_one("SELECT name, daily_price FROM daily_boards WHERE id = ? AND is_active=1", (daily_id,))
                if not row: return HttpResponse("Объявление не найдено", status=404)
                dname, dprice = row

                ok, avail, total = daily_available(daily_id, date_iso)
                if not ok:
                    return HttpResponse(f"Нет доступных предложений на эту дату (доступно {avail} из {total})", status=409)

                amount = float(dprice) * days
                amount, applied = apply_coupon(coupon_code, amount)

                q_exec("""
                  INSERT INTO bookings(
                    user_id, board_id, board_name, daily_board_id,
                    date, start_time, start_minute,
                    duration, quantity, amount,
                    status, payment_method, payment_status, coupon_code, created_at
                  ) VALUES(?, NULL, ?, ?, ?, NULL, NULL, ?, ?, ?, 'waiting_daily', 'site', 'unpaid', ?, datetime('now','localtime'))
                """, (tg_id, dname, daily_id, date_iso, days*24, qty, amount, applied))

        request.session["tg_id"] = tg_id
        return redirect(f"/user/{tg_id}/")
    except Exception as e:
        return HttpResponse(f"Ошибка брони: {e}", status=400)

# ---------- USER ----------
def user_dashboard(request, tg_id: int):
    ensure_schema()
    if _ensure_logged(request, tg_id):  # запрет чужих кабинетов
        return HttpResponse("forbidden", status=403)
    rows = q_all("""
        SELECT id, board_name, date, start_time, start_minute, duration, quantity, amount, status, payment_status
        FROM bookings
        WHERE user_id = ?
        ORDER BY id DESC
    """, (tg_id,))
    bookings = [{
        "id": r[0], "board": r[1], "date": r[2],
        "start_time": r[3], "start_minute": r[4],
        "duration": r[5], "quantity": r[6], "amount": r[7],
        "status": r[8], "payment_status": r[9] or "unpaid"
    } for r in rows]
    return render(request, "user.html", {"tg_id": tg_id, "bookings": bookings})

@require_POST
def user_cancel(request, tg_id: int, booking_id: int):
    ensure_schema()
    if _ensure_logged(request, tg_id):
        return HttpResponse("forbidden", status=403)
    row = q_one("SELECT status, payment_status FROM bookings WHERE id = ? AND user_id = ?", (booking_id, tg_id))
    if not row:
        return HttpResponseNotFound("Бронь не найдена")
    status, pstat = row
    if status in ("waiting_partner", "waiting_card", "waiting_cash", "waiting_daily") and pstat != "paid":
        q_exec("UPDATE bookings SET status='canceled' WHERE id = ?", (booking_id,))
    return redirect(f"/user/{tg_id}/")

# -----------------------------
# ONLINE PAYMENTS: YooKassa + webhooks + idempotency
# -----------------------------
def _booking_amount(booking_id:int):
    row = q_one("SELECT amount FROM bookings WHERE id = ?", (booking_id,))
    if not row: return None
    return (float(row[0]), 'RUB')

import requests

def _existing_pending_payment_url(booking_id:int):
    row = q_one("""
      SELECT confirmation_url, payload FROM payments
      WHERE booking_id=? AND provider='yookassa' AND status='pending'
      ORDER BY id DESC LIMIT 1
    """, (booking_id,))
    if not row: return None
    url, payload = row
    if url: return url
    try:
        data = json.loads(payload or "{}")
        return data.get("confirmation", {}).get("confirmation_url")
    except Exception:
        return None

def pay_yookassa(request, booking_id:int):
    ensure_schema()
    # доступ только владельцу брони
    tg_id = int(request.session.get("tg_id") or 0)
    owner = q_one("SELECT user_id FROM bookings WHERE id=?", (booking_id,))
    if not owner or int(owner[0]) != tg_id:
        return HttpResponse("forbidden", status=403)

    amt = _booking_amount(booking_id)
    if not amt:
        return HttpResponseNotFound("Бронь не найдена")
    amount, currency = amt

    # Идемпотентность: если уже есть pending — шлём туда
    pending_url = _existing_pending_payment_url(booking_id)
    if pending_url:
        return redirect(pending_url)

    shop_id = os.environ.get("YOOKASSA_SHOP_ID")
    secret = os.environ.get("YOOKASSA_SECRET_KEY")
    if not (shop_id and secret):
        return HttpResponse("ЮKassa не настроена (env).", status=500)

    idempotence_key = str(uuid.uuid4())
    cb_url = request.build_absolute_uri("/webhooks/yookassa/")
    conf_url = request.build_absolute_uri(f"/user/{request.session.get('tg_id','')}/")
    payload = {
        "amount": {"value": f"{amount:.2f}", "currency": currency},
        "capture": True,
        "confirmation": {"type": "redirect", "return_url": conf_url},
        "description": f"SUP Booking #{booking_id}",
        "metadata": {"booking_id": booking_id}
    }
    resp = requests.post(
        "https://api.yookassa.ru/v3/payments",
        auth=(shop_id, secret),
        headers={"Idempotence-Key": idempotence_key, "Content-Type":"application/json"},
        json=payload, timeout=30
    )
    if resp.status_code not in (200, 201):
        return HttpResponse(f"ЮKassa error: {resp.status_code} {resp.text}", status=502)
    data = resp.json()
    confirmation_url = (data.get("confirmation") or {}).get("confirmation_url")
    q_exec("""
      INSERT INTO payments(booking_id, provider, provider_payment_id, amount, currency, status, confirmation_url, payload)
      VALUES(?, 'yookassa', ?, ?, ?, ?, ?, ?)
    """, (booking_id, data.get("id"), amount, currency, data.get("status"), confirmation_url, json.dumps(data, ensure_ascii=False)))
    q_exec("UPDATE bookings SET payment_status='pending' WHERE id=?", (booking_id,))
    return redirect(confirmation_url or conf_url)

def _yookassa_fetch_payment(pid:str):
    shop_id = os.environ.get("YOOKASSA_SHOP_ID")
    secret = os.environ.get("YOOKASSA_SECRET_KEY")
    if not (shop_id and secret): return None
    r = requests.get(f"https://api.yookassa.ru/v3/payments/{pid}", auth=(shop_id, secret), timeout=30)
    if r.status_code != 200: return None
    return r.json()

@csrf_exempt
def webhook_yookassa(request):
    ensure_schema()
    try:
        data = json.loads(request.body.decode("utf-8"))
        pid = data.get("object", {}).get("id")
        status = data.get("object", {}).get("status")
        meta = data.get("object", {}).get("metadata", {})
        booking_id = int(meta.get("booking_id"))
    except Exception:
        return HttpResponse("bad", status=400)

    # обновим локально запись платежа
    q_exec("UPDATE payments SET status=?, payload=?, updated_at=CURRENT_TIMESTAMP WHERE provider='yookassa' AND provider_payment_id=?",
           (status, json.dumps(data, ensure_ascii=False), pid))

    # Сверка через API YooKassa (anti-spoof)
    safe = _yookassa_fetch_payment(pid)
    if not safe:
        return HttpResponse("bad", status=400)

    try:
        s_amount = float((safe.get("amount") or {}).get("value") or 0)
        s_currency = (safe.get("amount") or {}).get("currency")
        s_booking = int((safe.get("metadata") or {}).get("booking_id") or 0)
        if s_booking != booking_id:
            return HttpResponse("bad", status=400)
        bamt = _booking_amount(booking_id)
        if not bamt: return HttpResponse("bad", status=400)
        b_amount, b_cur = bamt
        if abs(s_amount - b_amount) > 0.01 or s_currency != b_cur:
            return HttpResponse("bad", status=400)
    except Exception:
        return HttpResponse("bad", status=400)

    status = safe.get("status")
    if status == "succeeded":
        q_exec("UPDATE bookings SET payment_status='paid', status=CASE WHEN status IN ('waiting_partner','waiting_card','waiting_cash','waiting_daily') THEN 'active' ELSE status END WHERE id=?", (booking_id,))
        # инкремент купона, если был применён
        crow = q_one("SELECT coupon_code FROM bookings WHERE id=?", (booking_id,))
        if crow and crow[0]:
            q_exec("UPDATE coupons SET used = COALESCE(used,0) + 1 WHERE code=?", (crow[0],))
    elif status in ("canceled","refunded"):
        q_exec("UPDATE bookings SET payment_status='failed' WHERE id=?", (booking_id,))

    return HttpResponse("ok")

# -----------------------------
# USER pay-card (реквизиты)
# -----------------------------
def user_pay_card(request, tg_id: int, booking_id: int):
    ensure_schema()
    if _ensure_logged(request, tg_id):
        return HttpResponse("forbidden", status=403)
    row = q_one("SELECT status FROM bookings WHERE id = ? AND user_id = ?", (booking_id, tg_id))
    if row and row[0] in ("waiting_partner", "waiting_cash", "waiting_daily"):
        q_exec("UPDATE bookings SET status='waiting_card', payment_method='card' WHERE id = ?", (booking_id,))
    details = os.environ.get("PAYMENT_CARD_DETAILS", "Переводите на карту XXXX XXXX XXXX XXXX Ф.И.О.")
    return HttpResponse(f"<html><body style='font-family:system-ui;padding:24px'>"
                        f"<h3>Оплата картой для брони #{booking_id}</h3>"
                        f"<p>{details}</p><p><a href='/user/{tg_id}/'>Назад</a></p></body></html>")

# ---------- PARTNER ----------
def partner_dashboard(request, tg_id: int):
    ensure_schema()
    if _ensure_logged(request, tg_id):
        return HttpResponse("forbidden", status=403)
    pid = partner_id_by_tg(tg_id)
    ctx = {"tg_id": tg_id, "partner_id": pid}
    if not pid:
        return render(request, "partner.html", ctx)

    bal = partner_balance(pid)
    ctx["balance"] = bal

    pending = q_all("""
        SELECT b.id, COALESCE(u.username, 'id:'||b.user_id), b.board_name, b.date, b.start_time, b.start_minute, b.duration, b.amount, b.payment_status
        FROM bookings b
        LEFT JOIN boards brd ON brd.id = b.board_id
        LEFT JOIN daily_boards db ON db.id = b.daily_board_id
        LEFT JOIN users u ON u.id = b.user_id
        WHERE COALESCE(brd.partner_id, db.partner_id) = ? AND b.status IN ('waiting_partner','waiting_card','waiting_cash','waiting_daily')
        ORDER BY b.id DESC
    """, (pid,))
    ctx["pending"] = [{
        "id": r[0],
        "user": r[1],
        "board": r[2], "date": r[3],
        "start_time": r[4], "start_minute": r[5],
        "duration": r[6], "amount": r[7], "payment_status": r[8] or "unpaid"
    } for r in pending]

    orders = q_all("""
        SELECT b.id, COALESCE(u.username, 'id:'||b.user_id), b.board_name, b.date, b.start_time, b.start_minute, b.duration, b.amount, b.status, b.payment_status
        FROM bookings b
        LEFT JOIN boards brd ON brd.id = b.board_id
        LEFT JOIN daily_boards db ON db.id = b.daily_board_id
        LEFT JOIN users u ON u.id = b.user_id
        WHERE COALESCE(brd.partner_id, db.partner_id) = ?
        ORDER BY b.id DESC LIMIT 50
    """, (pid,))
    ctx["orders"] = [{
        "id": r[0], "user": r[1], "board": r[2], "date": r[3],
        "start_time": r[4], "start_minute": r[5],
        "duration": r[6], "amount": r[7], "status": r[8], "payment_status": r[9] or "unpaid"
    } for r in orders]

    locs = q_all("SELECT id, name, COALESCE(latitude,0), COALESCE(longitude,0), COALESCE(kind,'spot') FROM locations WHERE partner_id = ? ORDER BY name", (pid,))
    ctx["locations"] = [{"id": r[0], "name": r[1], "lat": r[2], "lon": r[3], "kind": r[4]} for r in locs]
    boards = q_all("""
        SELECT brd.id, brd.name, COALESCE(l.name,'—'), brd.price, brd.total
        FROM boards brd LEFT JOIN locations l ON l.id = brd.location_id
        WHERE brd.partner_id = ? ORDER BY brd.id DESC
    """, (pid,))
    ctx["boards"] = [{"id":r[0], "name": r[1], "location": r[2], "price": r[3], "total": r[4]} for r in boards]

    drows = q_all("SELECT id, name, daily_price, COALESCE(address,''), available_quantity, is_active FROM daily_boards WHERE partner_id = ? ORDER BY id DESC", (pid,))
    ctx["daily_boards"] = [{"id":r[0],"name": r[1],"daily_price": r[2],"address": r[3],"available_quantity": r[4],"is_active": r[5]} for r in drows]

    cp = q_all("SELECT code, type, value, COALESCE(used,0), COALESCE(max_uses,''), COALESCE(valid_from,''), COALESCE(valid_to,''), active FROM coupons WHERE partner_id IS NULL OR partner_id = ? ORDER BY id DESC LIMIT 30", (pid,))
    ctx["coupons"] = [{"code":r[0],"type":r[1],"value":r[2],"used":r[3],"max_uses":r[4],"valid_from":r[5],"valid_to":r[6],"active":r[7]} for r in cp]

    wd = q_all("""
        SELECT id, amount, status, created_at
        FROM partner_withdraw_requests WHERE partner_id = ?
        ORDER BY id DESC LIMIT 5
    """, (pid,))
    ctx["last_withdraws"] = [{"id": r[0], "amount": r[1], "status": r[2], "created_at": r[3]} for r in wd]

    ctx.update({
        "ymaps_api": ymaps_api_url(),
        "default_lat": float(os.environ.get("MAP_DEFAULT_LAT", "55.751244")),
        "default_lon": float(os.environ.get("MAP_DEFAULT_LON", "37.618423")),
        "default_zoom": int(os.environ.get("MAP_DEFAULT_ZOOM", "11")),
        "partner_markers_json": json.dumps([{"lat":x[2],"lon":x[3],"name":x[1],"kind":x[4]} for x in locs], ensure_ascii=False)
    })
    ctx["csrf_token"] = csrf_token(request)
    return render(request, "partner.html", ctx)

def partner_become(request, tg_id: int):
    ensure_schema()
    if _ensure_logged(request, tg_id):
        return HttpResponse("forbidden", status=403)
    if not partner_id_by_tg(tg_id):
        q_exec("INSERT INTO partners(name, telegram_id, is_approved) VALUES(?, ?, 0)", (f"Партнёр {tg_id}", tg_id))
    return redirect(f"/partner/{tg_id}/")

@require_POST
def partner_withdraw(request, tg_id: int):
    ensure_schema()
    if _ensure_logged(request, tg_id):
        return HttpResponse("forbidden", status=403)
    pid = partner_id_by_tg(tg_id)
    if not pid:
        return redirect(f"/partner/{tg_id}/")
    try:
        amount = float(request.POST.get("amount", "0"))
    except Exception:
        amount = 0
    if amount < 500 or amount > partner_balance(pid):
        return redirect(f"/partner/{tg_id}/")
    last = q_one("""
        SELECT created_at FROM partner_withdraw_requests
        WHERE partner_id = ?
        ORDER BY id DESC LIMIT 1
    """, (pid,))
    if last:
        try:
            last_dt = datetime.fromisoformat(last[0].split(".")[0])
            if datetime.now() - last_dt < timedelta(hours=24):
                return redirect(f"/partner/{tg_id}/")
        except Exception:
            pass
    q_exec("INSERT INTO partner_withdraw_requests(partner_id, amount, status) VALUES(?, ?, 'pending')", (pid, amount))
    return redirect(f"/partner/{tg_id}/")

@require_POST
def partner_add_location(request, tg_id: int):
    ensure_schema()
    if _ensure_logged(request, tg_id): return HttpResponse("forbidden", status=403)
    pid = partner_id_by_tg(tg_id)
    if not pid: return redirect(f"/partner/{tg_id}/")
    name = (request.POST.get("name") or "").strip()
    lat = request.POST.get("lat") or None
    lon = request.POST.get("lon") or None
    kind = request.POST.get("kind") or "spot"
    latv = float(lat) if lat else None
    lonv = float(lon) if lon else None
    if name:
        q_exec("INSERT INTO locations(name, partner_id, is_active, latitude, longitude, kind) VALUES(?, ?, 1, ?, ?, ?)", (name, pid, latv, lonv, kind))
    return redirect(f"/partner/{tg_id}/")

@require_POST
def partner_add_board(request, tg_id: int):
    ensure_schema()
    if _ensure_logged(request, tg_id): return HttpResponse("forbidden", status=403)
    pid = partner_id_by_tg(tg_id)
    if not pid: return redirect(f"/partner/{tg_id}/")
    name = (request.POST.get("name") or "").strip()
    try:
        price = float(request.POST.get("price", "0"))
        qty = int(request.POST.get("qty", "0"))
        loc_id = int(request.POST.get("location_id", "0"))
    except Exception:
        return redirect(f"/partner/{tg_id}/")
    if name and qty > 0 and price > 0:
        q_exec("""
            INSERT INTO boards(name, description, total, quantity, price, is_active, partner_id, location_id)
            VALUES(?, '', ?, ?, ?, 1, ?, ?)
        """, (name, qty, qty, price, pid, loc_id))
    return redirect(f"/partner/{tg_id}/")

@require_POST
def partner_add_daily(request, tg_id:int):
    ensure_schema()
    if _ensure_logged(request, tg_id): return HttpResponse("forbidden", status=403)
    pid = partner_id_by_tg(tg_id)
    if not pid: return redirect(f"/partner/{tg_id}/")
    name = (request.POST.get("name") or "").strip()
    try:
        price = float(request.POST.get("price") or 0)
        qty = int(request.POST.get("qty") or 1)
    except Exception:
        price, qty = 0, 0
    addr = (request.POST.get("address") or "").strip()
    if name and price>0 and qty>0:
        q_exec("INSERT INTO daily_boards(name, daily_price, address, available_quantity, is_active, partner_id) VALUES(?, ?, ?, ?, 1, ?)", (name, price, addr, qty, pid))
    return redirect(f"/partner/{tg_id}/")

@require_POST
def partner_add_coupon(request, tg_id:int):
    ensure_schema()
    if _ensure_logged(request, tg_id): return HttpResponse("forbidden", status=403)
    code = (request.POST.get("code") or "").strip()
    ctype = request.POST.get("ctype") or "percent"
    try:
        value = float(request.POST.get("value") or 0)
    except Exception:
        value = 0
    max_uses = request.POST.get("max_uses") or None
    period = (request.POST.get("period") or "").strip()
    vf, vt = None, None
    if ".." in period:
        left, right = period.split("..",1)
        vf = (left.strip() or None)
        vt = (right.strip() or None)
    if code and value>0:
        try:
            q_exec("INSERT INTO coupons(code, type, value, max_uses, valid_from, valid_to, active) VALUES(?, ?, ?, ?, ?, ?, 1)", (code, ctype, value, int(max_uses) if max_uses else None, vf, vt))
        except Exception:
            pass
    return redirect(f"/partner/{tg_id}/")

@require_POST
def partner_confirm(request, tg_id: int, booking_id: int):
    ensure_schema()
    if _ensure_logged(request, tg_id): return HttpResponse("forbidden", status=403)
    pid = partner_id_by_tg(tg_id)
    if not pid:
        return redirect(f"/partner/{tg_id}/")
    own = q_one("""
        SELECT 1
        FROM bookings b
        LEFT JOIN boards brd ON brd.id=b.board_id
        LEFT JOIN daily_boards db ON db.id=b.daily_board_id
        WHERE b.id = ? AND COALESCE(brd.partner_id, db.partner_id) = ?
    """, (booking_id, pid))
    if own:
        q_exec("UPDATE bookings SET status='active' WHERE id = ? AND status IN ('waiting_partner','waiting_card','waiting_cash','waiting_daily')", (booking_id,))
    return redirect(f"/partner/{tg_id}/")

@require_POST
def partner_cancel(request, tg_id: int, booking_id: int):
    ensure_schema()
    if _ensure_logged(request, tg_id): return HttpResponse("forbidden", status=403)
    pid = partner_id_by_tg(tg_id)
    if not pid: return redirect(f"/partner/{tg_id}/")
    row = q_one("""
        SELECT b.status
        FROM bookings b
        LEFT JOIN boards brd ON brd.id=b.board_id
        LEFT JOIN daily_boards db ON db.id=b.daily_board_id
        WHERE b.id = ? AND COALESCE(brd.partner_id, db.partner_id) = ?
    """, (booking_id, pid))
    if row and row[0] in ("waiting_partner","waiting_card","waiting_cash","active","waiting_daily"):
        q_exec("UPDATE bookings SET status='canceled' WHERE id = ?", (booking_id,))
    return redirect(f"/partner/{tg_id}/")

@require_POST
def partner_complete(request, tg_id: int, booking_id: int):
    ensure_schema()
    if _ensure_logged(request, tg_id):
        return HttpResponse("forbidden", status=403)
    pid = partner_id_by_tg(tg_id)
    if not pid:
        return redirect(f"/partner/{tg_id}/")

    row = q_one("""
        SELECT b.status, b.payment_status
        FROM bookings b
        LEFT JOIN boards brd ON brd.id = b.board_id
        LEFT JOIN daily_boards db ON db.id = b.daily_board_id
        WHERE b.id = ? AND COALESCE(brd.partner_id, db.partner_id) = ?
    """, (booking_id, pid))

    if row and row[0] == "active":
        q_exec("UPDATE bookings SET status='completed', ended_at=datetime('now','localtime') WHERE id=?", (booking_id,))
        # единоразовое начисление партнёру (если оплачено и ещё не начислялось)
        _credit_partner_if_needed(booking_id)

    return redirect(f"/partner/{tg_id}/")

# ---------- EMPLOYEE ----------
def _employee_partner_ids(tg_id: int):
    rows = q_all("SELECT partner_id FROM employees WHERE telegram_id = ?", (str(tg_id),))
    return [r[0] for r in rows]

def employee_dashboard(request, tg_id: int):
    ensure_schema()
    if _ensure_logged(request, tg_id):
        return HttpResponse("forbidden", status=403)

    pids = _employee_partner_ids(tg_id)
    partners = [str(pid) for pid in pids] if pids else []

    today_iso = date.today().isoformat()
    if pids:
        rows = q_all(f"""
            SELECT b.id, COALESCE(u.username, 'id:'||b.user_id) as user,
                   b.board_name, b.date, b.start_time, b.start_minute,
                   b.duration, b.amount, b.payment_status, b.status
            FROM bookings b
            LEFT JOIN boards brd ON brd.id=b.board_id
            LEFT JOIN daily_boards db ON db.id=b.daily_board_id
            LEFT JOIN users u ON u.id=b.user_id
            WHERE b.date=? AND COALESCE(brd.partner_id, db.partner_id) IN ({','.join(['?']*len(pids))})
            ORDER BY b.id DESC
        """, (today_iso, *pids))
    else:
        rows = []

    bookings = [{
        "id": r[0], "user": r[1], "board": r[2], "date": r[3],
        "start_time": r[4], "start_minute": r[5],
        "duration": r[6], "amount": r[7],
        "payment_status": r[8] or "unpaid",
        "status": r[9]
    } for r in rows]

    return render(request, "employee.html", {"tg_id": tg_id, "partners": partners, "bookings": bookings})

def _booking_partner(booking_id: int):
    return _booking_partner_id(booking_id)

def _employee_can_touch(tg_id: int, booking_id: int) -> bool:
    pids = set(_employee_partner_ids(tg_id))
    bid_pid = _booking_partner(booking_id)
    return bid_pid in pids if bid_pid is not None else False

def _employee_credit_if_needed(employee_tg_id: int, booking_id: int):
    # уже зачисляли этому сотруднику за эту бронь?
    if q_one("SELECT 1 FROM employee_wallet_ops WHERE employee_telegram_id=? AND booking_id=?", (str(employee_tg_id), booking_id)):
        return
    # найдём партнёра/процент
    pid = _booking_partner_id(booking_id)
    if pid is None:
        return
    row = q_one("SELECT commission_percent FROM employees WHERE telegram_id=? AND partner_id=?", (str(employee_tg_id), pid))
    if not row:
        return
    pct = float(row[0] or 0)
    amt_row = q_one("SELECT amount, payment_status FROM bookings WHERE id=?", (booking_id,))
    if not amt_row:
        return
    if (amt_row[1] or "unpaid") != "paid":
        return
    base = float(amt_row[0] or 0)
    reward = round(base * pct / 100.0, 2)
    if reward <= 0:
        return
    q_exec("""
        INSERT INTO employee_wallet_ops(employee_telegram_id, booking_id, amount, src, created_at)
        VALUES(?, ?, ?, 'booking_commission', datetime('now','localtime'))
    """, (str(employee_tg_id), booking_id, reward))

@require_POST
def employee_confirm(request, tg_id: int, booking_id: int):
    ensure_schema()
    if _ensure_logged(request, tg_id):
        return HttpResponse("forbidden", status=403)
    if _employee_can_touch(tg_id, booking_id):
        q_exec("UPDATE bookings SET status='active' WHERE id=? AND status IN ('waiting_partner','waiting_card','waiting_cash','waiting_daily')", (booking_id,))
    return redirect(f"/employee/{tg_id}/")

@require_POST
def employee_cancel(request, tg_id: int, booking_id: int):
    ensure_schema()
    if _ensure_logged(request, tg_id):
        return HttpResponse("forbidden", status=403)
    if _employee_can_touch(tg_id, booking_id):
        q_exec("UPDATE bookings SET status='canceled' WHERE id=? AND status IN ('waiting_partner','waiting_card','waiting_cash','active','waiting_daily')", (booking_id,))
    return redirect(f"/employee/{tg_id}/")

@require_POST
def employee_complete(request, tg_id: int, booking_id: int):
    ensure_schema()
    if _ensure_logged(request, tg_id):
        return HttpResponse("forbidden", status=403)
    if _employee_can_touch(tg_id, booking_id):
        q_exec("UPDATE bookings SET status='completed', ended_at=datetime('now','localtime') WHERE id=? AND status='active'", (booking_id,))
        _credit_partner_if_needed(booking_id)
        _employee_credit_if_needed(tg_id, booking_id)
    return redirect(f"/employee/{tg_id}/")

# ---------- MOBILE EMPLOYEE ----------
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

def mobile_employee(request, tg_id: int):
    ensure_schema()
    if _ensure_logged(request, tg_id):
        return HttpResponse("forbidden", status=403)
    # список сегодняшних броней сотрудника
    pids = _employee_partner_ids(tg_id)
    today_iso = date.today().isoformat()
    bookings = []
    if pids:
        rows = q_all(f"""
            SELECT b.id, b.board_name, b.date, b.start_time, b.start_minute, b.duration, b.amount, b.payment_status,
                   b.started_at, b.ended_at
            FROM bookings b
            LEFT JOIN boards brd ON brd.id=b.board_id
            LEFT JOIN daily_boards db ON db.id=b.daily_board_id
            WHERE b.date=? AND COALESCE(brd.partner_id, db.partner_id) IN ({','.join(['?']*len(pids))})
            ORDER BY b.id DESC
        """, (today_iso, *pids))
        for r in rows:
            photos = q_all("SELECT type, url FROM booking_photos WHERE booking_id=? ORDER BY id", (r[0],))
            bookings.append({
                "id": r[0], "board": r[1], "date": r[2], "start_time": r[3], "start_minute": r[4],
                "duration": r[5], "amount": r[6], "payment_status": r[7] or "unpaid",
                "started_at": r[8], "ended_at": r[9],
                "photos": [{"type": ph[0], "url": ph[1]} for ph in photos]
            })
    return render(request, "mobile_employee.html", {"tg_id": tg_id, "bookings": bookings, "today": today_iso})

@require_POST
def mobile_booking_start(request, tg_id: int, booking_id: int):
    ensure_schema()
    if _ensure_logged(request, tg_id): return HttpResponse("forbidden", status=403)
    if _employee_can_touch(tg_id, booking_id):
        q_exec("UPDATE bookings SET started_at=datetime('now','localtime') WHERE id=? AND started_at IS NULL", (booking_id,))
    return redirect(f"/m/{tg_id}/")

@require_POST
def mobile_booking_stop(request, tg_id: int, booking_id: int):
    ensure_schema()
    if _ensure_logged(request, tg_id): return HttpResponse("forbidden", status=403)
    if _employee_can_touch(tg_id, booking_id):
        q_exec("UPDATE bookings SET ended_at=datetime('now','localtime') WHERE id=? AND ended_at IS NULL", (booking_id,))
    return redirect(f"/m/{tg_id}/")

@require_POST
def mobile_upload_photo(request, tg_id: int, booking_id: int):
    ensure_schema()
    if _ensure_logged(request, tg_id): return HttpResponse("forbidden", status=403)
    if not _employee_can_touch(tg_id, booking_id):
        return HttpResponse("forbidden", status=403)
    ptype = (request.POST.get("ptype") or "before")
    file = request.FILES.get("photo")
    if file:
        # простое сохранение (без обработки EXIF и т.п.)
        ext = os.path.splitext(file.name)[1] or ".jpg"
        name = f"b{booking_id}_{ptype}_{uuid.uuid4().hex[:8]}{ext}"
        path = os.path.join(UPLOAD_DIR, name)
        with open(path, "wb") as f:
            for chunk in file.chunks():
                f.write(chunk)
        url = f"/uploads/{name}"
        q_exec("INSERT INTO booking_photos(booking_id, type, url) VALUES(?, ?, ?)", (booking_id, ptype, url))
    return redirect(f"/m/{tg_id}/")

def mobile_act(request, tg_id: int, booking_id: int):
    ensure_schema()
    if _ensure_logged(request, tg_id): return HttpResponse("forbidden", status=403)
    if not _employee_can_touch(tg_id, booking_id): return HttpResponse("forbidden", status=403)
    row = q_one("""
        SELECT b.id, b.user_id, COALESCE(u.full_name, COALESCE(u.username, 'id:'||b.user_id)) as uname,
               b.board_name, b.date, b.duration, b.amount, b.payment_status, b.status
        FROM bookings b
        LEFT JOIN users u ON u.id=b.user_id
        WHERE b.id=?
    """, (booking_id,))
    if not row:
        return HttpResponseNotFound("not found")
    html = f"""
    <html><head><meta charset="utf-8"><title>Акт #{row[0]}</title>
    <style>body{{font-family:system-ui;padding:24px}} .muted{{color:#666}}</style></head>
    <body>
      <h3>Акт оказания услуги #{row[0]}</h3>
      <div class="muted">Дата: {date.today().isoformat()}</div>
      <hr>
      <p><b>Клиент:</b> {row[2]} (tg_id: {row[1]})</p>
      <p><b>Услуга:</b> Аренда «{row[3]}», дата {row[4]}, длительность {row[5]} ч.</p>
      <p><b>Сумма:</b> {row[6]:.2f} ₽ · оплата: {row[7]}</p>
      <p><b>Статус брони:</b> {row[8]}</p>
      <p class="muted">Подписано электронной отметкой сотрудника tg:{tg_id}.</p>
    </body></html>"""
    return HttpResponse(html)

# ---------- OWNER (витрина) ----------
def owner_showcase(request, partner_id: int):
    ensure_schema()
    prow = q_one("SELECT COALESCE(name,'Партнёр') FROM partners WHERE id=?", (partner_id,))
    if not prow:
        return HttpResponseNotFound("Партнёр не найден")
    name = prow[0]
    rating_row = q_one("SELECT COALESCE(AVG(value),0), COUNT(*) FROM ratings WHERE partner_id=?", (partner_id,))
    rating = float(rating_row[0] or 0)
    rcount = int(rating_row[1] or 0)

    boards = q_all("""
        SELECT brd.name, COALESCE(l.name,'—'), brd.price, brd.total
        FROM boards brd LEFT JOIN locations l ON l.id=brd.location_id
        WHERE brd.partner_id = ? AND COALESCE(brd.is_active,1)=1
        ORDER BY brd.id DESC
    """, (partner_id,))
    daily = q_all("""
        SELECT name, daily_price, COALESCE(address,''), available_quantity
        FROM daily_boards
        WHERE partner_id=? AND is_active=1
        ORDER BY id DESC
    """, (partner_id,))
    ctx = {
        "pid": partner_id,
        "name": name,
        "rating": rating,
        "reviews_count": rcount,
        "deposit_insurance": "включена" if rating >= 4.5 else "—",
        "boards": [{"name":r[0], "location": r[1], "price": r[2], "total": r[3]} for r in boards],
        "daily": [{"name":r[0], "daily_price": r[1], "address": r[2], "available_quantity": r[3]} for r in daily],
    }
    return render(request, "owner.html", ctx)

# ---------- ADMIN ----------
def _is_admin(uid:int) -> bool:
    return bool(q_one("SELECT 1 FROM admins WHERE user_id=?", (uid,)))

def _ensure_admin(request, tg_id:int):
    if _ensure_logged(request, tg_id):
        return HttpResponse("forbidden", status=403)
    if not _is_admin(tg_id):
        return HttpResponse("forbidden", status=403)
    return None

def admin_dashboard(request, tg_id: int):
    ensure_schema()
    forb = _ensure_admin(request, tg_id)
    if forb: return forb

    stat = {
        "partners": q_one("SELECT COUNT(*) FROM partners")[0],
        "users": q_one("SELECT COUNT(*) FROM users")[0],
        "today_bookings": q_one("SELECT COUNT(*) FROM bookings WHERE date=?", (date.today().isoformat(),))[0],
    }
    rows = q_all("""
        SELECT b.id, COALESCE(u.username, 'id:'||b.user_id), b.board_name, b.date, b.start_time, b.start_minute,
               b.duration, b.amount, b.status, b.payment_status
        FROM bookings b LEFT JOIN users u ON u.id=b.user_id
        ORDER BY b.id DESC LIMIT 100
    """)
    bookings = [{
        "id": r[0], "user": r[1], "board": r[2], "date": r[3],
        "start_time": r[4], "start_minute": r[5], "duration": r[6], "amount": r[7],
        "status": r[8], "payment_status": r[9] or "unpaid"
    } for r in rows]
    return render(request, "admin.html", {"tg_id": tg_id, "stat": stat, "bookings": bookings})

@require_POST
def admin_booking_activate(request, tg_id:int, booking_id:int):
    ensure_schema()
    forb = _ensure_admin(request, tg_id)
    if forb: return forb
    q_exec("UPDATE bookings SET status='active' WHERE id=? AND status IN ('waiting_partner','waiting_card','waiting_cash','waiting_daily')", (booking_id,))
    return redirect(f"/admin/{tg_id}/")

@require_POST
def admin_booking_complete(request, tg_id:int, booking_id:int):
    ensure_schema()
    forb = _ensure_admin(request, tg_id)
    if forb: return forb
    q_exec("UPDATE bookings SET status='completed', ended_at=datetime('now','localtime') WHERE id=? AND status IN ('active','waiting_daily')", (booking_id,))
    _credit_partner_if_needed(booking_id)
    return redirect(f"/admin/{tg_id}/")

@require_POST
def admin_booking_cancel(request, tg_id:int, booking_id:int):
    ensure_schema()
    forb = _ensure_admin(request, tg_id)
    if forb: return forb
    q_exec("UPDATE bookings SET status='canceled' WHERE id=?", (booking_id,))
    return redirect(f"/admin/{tg_id}/")

def admin_finance(request, tg_id:int):
    ensure_schema()
    forb = _ensure_admin(request, tg_id)
    if forb: return forb

    revenue = float(q_one("SELECT COALESCE(SUM(amount),0) FROM bookings WHERE payment_status='paid'")[0] or 0)
    expenses = float(q_one("SELECT COALESCE(SUM(amount),0) FROM expenses")[0] or 0)
    commission = platform_commission_percent()
    profit = revenue - expenses  # упрощённо

    withdraws = [{
        "id": r[0], "partner_id": r[1], "amount": r[2], "status": r[3], "created_at": r[4]
    } for r in q_all("SELECT id, partner_id, amount, status, created_at FROM partner_withdraw_requests ORDER BY id DESC LIMIT 100")]

    expenses_rows = [{
        "id": r[0], "date": r[1], "amount": r[2], "description": r[3]
    } for r in q_all("SELECT id, date, amount, COALESCE(description,'') FROM expenses ORDER BY id DESC LIMIT 100")]

    ctx = {
        "tg_id": tg_id,
        "money": {"revenue": revenue, "expenses": expenses, "profit": profit},
        "commission": commission,
        "withdraws": withdraws,
        "expenses": expenses_rows,
        "today": date.today().isoformat()
    }
    return render(request, "admin_finance.html", ctx)

@require_POST
def admin_set_global_commission(request, tg_id:int):
    ensure_schema()
    forb = _ensure_admin(request, tg_id)
    if forb: return forb
    try:
        val = float(request.POST.get("value") or 10)
    except Exception:
        val = 10.0
    set_setting("PLATFORM_COMMISSION_PERCENT", f"{val}")
    return redirect(f"/admin/{tg_id}/finance/")

@require_POST
def admin_add_expense(request, tg_id:int):
    ensure_schema()
    forb = _ensure_admin(request, tg_id)
    if forb: return forb
    d = (request.POST.get("date") or date.today().isoformat()).strip()
    try:
        amt = float(request.POST.get("amount") or 0)
    except Exception:
        amt = 0
    desc = (request.POST.get("description") or "").strip()
    if amt > 0:
        q_exec("INSERT INTO expenses(date, amount, description) VALUES(?,?,?)", (d, amt, desc))
    return redirect(f"/admin/{tg_id}/finance/")

@require_POST
def admin_delete_expense(request, tg_id:int, expense_id:int):
    ensure_schema()
    forb = _ensure_admin(request, tg_id)
    if forb: return forb
    q_exec("DELETE FROM expenses WHERE id=?", (expense_id,))
    return redirect(f"/admin/{tg_id}/finance/")

@require_POST
def admin_withdraw_approve(request, tg_id:int, wid:int):
    ensure_schema()
    forb = _ensure_admin(request, tg_id)
    if forb: return forb
    row = q_one("SELECT partner_id, amount, status FROM partner_withdraw_requests WHERE id=?", (wid,))
    if row and row[2] == "pending":
        pid, amount = row[0], float(row[1])
        q_exec("""
            INSERT INTO partner_wallet_ops(partner_id, type, amount, src, created_at)
            VALUES(?, 'debit', ?, 'withdraw', datetime('now','localtime'))
        """, (pid, amount))
        q_exec("UPDATE partner_withdraw_requests SET status='approved' WHERE id=?", (wid,))
    return redirect(f"/admin/{tg_id}/finance/")

@require_POST
def admin_withdraw_reject(request, tg_id:int, wid:int):
    ensure_schema()
    forb = _ensure_admin(request, tg_id)
    if forb: return forb
    q_exec("UPDATE partner_withdraw_requests SET status='rejected' WHERE id=?", (wid,))
    return redirect(f"/admin/{tg_id}/finance/")

def admin_finance_partner(request, tg_id:int, pid:int):
    ensure_schema()
    forb = _ensure_admin(request, tg_id)
    if forb: return forb
    balance = partner_balance(pid)
    commission = partner_effective_commission(pid)
    return render(request, "admin_finance_partner.html", {"tg_id": tg_id, "pid": pid, "balance": balance, "commission": commission})

@require_POST
def admin_finance_partner_set_commission(request, tg_id:int, pid:int):
    ensure_schema()
    forb = _ensure_admin(request, tg_id)
    if forb: return forb
    try:
        val = float(request.POST.get("value") or 10)
    except Exception:
        val = 10.0
    q_exec("UPDATE partners SET commission_percent=? WHERE id=?", (val, pid))
    return redirect(f"/admin/{tg_id}/finance/partner/{pid}/")

# ---------- EXPORTS ----------
def export_bookings_csv(request, tg_id:int):
    ensure_schema()
    forb = _ensure_admin(request, tg_id)
    if forb: return forb
    rows = q_all("""
        SELECT id, user_id, board_name, date, start_time, start_minute, duration, quantity, amount, status, payment_status, created_at
        FROM bookings ORDER BY id DESC
    """)
    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="bookings.csv"'
    w = csv.writer(resp)
    w.writerow(["id","user_id","board","date","start_h","start_m","hours","qty","amount","status","payment","created_at"])
    for r in rows:
        w.writerow(r)
    return resp

def export_payments_csv(request, tg_id:int):
    ensure_schema()
    forb = _ensure_admin(request, tg_id)
    if forb: return forb
    rows = q_all("""
        SELECT id, booking_id, provider, provider_payment_id, amount, currency, status, created_at, updated_at
        FROM payments ORDER BY id DESC
    """)
    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="payments.csv"'
    w = csv.writer(resp)
    w.writerow(["id","booking_id","provider","provider_payment_id","amount","currency","status","created_at","updated_at"])
    for r in rows:
        w.writerow(r)
    return resp

# ---------- STATIC UPLOADS SERVE ----------
def serve_upload(request, fname:str):
    # простая раздача сохранённых файлов (без X-Accel). Защита от path traversal.
    safe = os.path.normpath(fname).lstrip(os.sep)
    path = os.path.join(UPLOAD_DIR, safe)
    if not os.path.isfile(path):
        return HttpResponseNotFound("not found")
    with open(path, "rb") as f:
        data = f.read()
    # контент-тайп по расширению
    ext = os.path.splitext(path)[1].lower()
    ctype = "image/jpeg" if ext in (".jpg",".jpeg") else "image/png" if ext == ".png" else "application/octet-stream"
    resp = HttpResponse(data, content_type=ctype)
    return resp

# -----------------------------
# URLS
# -----------------------------
urlpatterns = [
    path("", landing),
    path("about/", about),

    path("signup/", signup),
    path("login/", login_view),
    path("logout/", logout_view),

    path("book/", book),

    # User
    path("user/<int:tg_id>/", user_dashboard),
    path("user/<int:tg_id>/cancel/<int:booking_id>/", user_cancel),
    path("user/<int:tg_id>/pay-card/<int:booking_id>/", user_pay_card),

    # Payments
    path("pay/<int:booking_id>/yookassa/", pay_yookassa),
    path("webhooks/yookassa/", webhook_yookassa),

    # Partner
    path("partner/<int:tg_id>/", partner_dashboard),
    path("partner/<int:tg_id>/become/", partner_become),
    path("partner/<int:tg_id>/withdraw/", partner_withdraw),
    path("partner/<int:tg_id>/add-location/", partner_add_location),
    path("partner/<int:tg_id>/add-board/", partner_add_board),
    path("partner/<int:tg_id>/add-daily/", partner_add_daily),
    path("partner/<int:tg_id>/add-coupon/", partner_add_coupon),
    path("partner/<int:tg_id>/confirm/<int:booking_id>/", partner_confirm),
    path("partner/<int:tg_id>/cancel/<int:booking_id>/", partner_cancel),
    path("partner/<int:tg_id>/complete/<int:booking_id>/", partner_complete),

    # Employee
    path("employee/<int:tg_id>/", employee_dashboard),
    path("employee/<int:tg_id>/confirm/<int:booking_id>/", employee_confirm),
    path("employee/<int:tg_id>/cancel/<int:booking_id>/", employee_cancel),
    path("employee/<int:tg_id>/complete/<int:booking_id>/", employee_complete),

    # Mobile
    path("m/<int:tg_id>/", mobile_employee),
    path("m/<int:tg_id>/booking/<int:booking_id>/start/", mobile_booking_start),
    path("m/<int:tg_id>/booking/<int:booking_id>/stop/", mobile_booking_stop),
    path("m/<int:tg_id>/photo/<int:booking_id>/", mobile_upload_photo),
    path("m/<int:tg_id>/act/<int:booking_id>/", mobile_act),

    # Owner showcase
    path("owner/<int:partner_id>/", owner_showcase),

    # Admin
    path("admin/<int:tg_id>/", admin_dashboard),
    path("admin/<int:tg_id>/booking/<int:booking_id>/activate/", admin_booking_activate),
    path("admin/<int:tg_id>/booking/<int:booking_id>/complete/", admin_booking_complete),
    path("admin/<int:tg_id>/booking/<int:booking_id>/cancel/", admin_booking_cancel),
    path("admin/<int:tg_id>/finance/", admin_finance),
    path("admin/<int:tg_id>/finance/export/bookings/", export_bookings_csv),
    path("admin/<int:tg_id>/finance/export/payments/", export_payments_csv),
    path("admin/<int:tg_id>/finance/add-expense/", admin_add_expense),
    path("admin/<int:tg_id>/finance/expense/<int:expense_id>/delete/", admin_delete_expense),
    path("admin/<int:tg_id>/finance/set-commission/", admin_set_global_commission),
    path("admin/<int:tg_id>/withdraw/<int:wid>/approve/", admin_withdraw_approve),
    path("admin/<int:tg_id>/withdraw/<int:wid>/reject/", admin_withdraw_reject),
    path("admin/<int:tg_id>/finance/partner/<int:pid>/", admin_finance_partner),
    path("admin/<int:tg_id>/finance/partner/<int:pid>/set-commission/", admin_finance_partner_set_commission),

    # uploads
    re_path(r"^uploads/(?P<fname>.+)$", serve_upload),
]

# -----------------------------
# Entry
# -----------------------------
if __name__ == "__main__":
    ensure_schema()
    ensure_admins_from_env()
    execute_from_command_line(sys.argv)
