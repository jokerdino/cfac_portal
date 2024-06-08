from extensions import db

class Announcements(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    created_by = db.Column(db.String)
    created_on = db.Column(db.DateTime)

    txt_title = db.Column(db.Text)
    txt_message = db.Column(db.Text)
