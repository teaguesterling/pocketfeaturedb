from flask import current_app
from drake.extensions import (
    celery,
    login_manager,
    db,
)
from .models import User


@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


def create_user(username, email, password=None, **fields):
    # Don't allow admin to be set at creation time
    fields.pop('is_admin')
    already_active = not current_app.config.get('USERS_REQUIRE_EMAIL_CONFIRMATION', False)
    user = User(username=username,
                email=email,
                password=password,
                active=already_active,
                **fields)

    with db.session.in_transaction as (session, transaction):
        session.add(user)
        transaction.commit()

    if not already_active:
        send_registration_confirmation_email(user)

    return user


@celery.task('user__send_registration_confirmation_email')
def send_registration_confirmation_email(user):
    raise NotImplementedError("User confirmation not yet implemented")
