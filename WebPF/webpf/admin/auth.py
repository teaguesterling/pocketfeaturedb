from flask import (
    redirect,
    request,
    url_for,
)
from flask.ext import (
    admin,
    login,
)
from drake.data.user.forms import LoginForm


def current_user_is_admin():
    user = login.current_user
    return user is not None and \
           user.is_authenticated() and \
           user.is_admin


class AuthenticatedMixin(object):
    def is_accessible(self):
        return current_user_is_admin()


class AdminLoginForm(LoginForm):
    def validate(self):
        preliminary_validation = super(AdminLoginForm, self).validate()
        if not preliminary_validation:
            return False
        if not self.user.is_admin:
            self.username.errors.append("User not authorized")
            return False
        return True


class AuthenticatedAdminIndexView(admin.AdminIndexView):

    @admin.expose('/')
    def index(self):
        if not current_user_is_admin():
            return redirect(url_for('.login'))
        return super(AuthenticatedAdminIndexView, self).index()

    @admin.expose('/login', methods=('GET', 'POST'))
    def login(self):
        # handle user login
        form = AdminLoginForm(request.form)
        if admin.helpers.validate_form_on_submit(form):
            login.login_user(form.user, remember=form.remember)

        if current_user_is_admin():
            return redirect(url_for('.index'))

        self._template_args['form'] = form
        self._template_args['link'] = 'Administrator Login'

        render_index = super(AuthenticatedAdminIndexView, self).index
        return render_index()

    @admin.expose('/logout')
    def logout(self):
        login.logout_user()
        return redirect(url_for('.index'))
