from flask_login import UserMixin


class User(UserMixin):
    def __init__(self, id, email, is_admin=False):
        self.id = id
        self.email = email
        self.is_admin = is_admin

    def get_id(self):
        return str(self.id)