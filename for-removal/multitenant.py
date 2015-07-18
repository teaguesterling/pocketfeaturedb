class TenantMixin(object):
    def get_id(self):
        return None

    def is_permitted(self, user):
        return False


current_tenant = TenantMixin()
