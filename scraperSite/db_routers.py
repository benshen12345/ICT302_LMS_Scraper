class MoodleRouter:
    """
    Routes Moodle models to the Moodle DB (read-only) and other models to default.
    Disallows migrations or writes to Moodle DB.
    """

    MOODLE_MODELS = ['course']  # lowercase model names that exist in Moodle

    def db_for_read(self, model, **hints):
        if model._meta.model_name in self.MOODLE_MODELS:
            return 'moodle'
        return 'default'

    def db_for_write(self, model, **hints):
        if model._meta.model_name in self.MOODLE_MODELS:
            return None  # disallow writes to Moodle
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        # Allow relations if both objects are in the same database
        db_list = ('default', 'moodle')
        if obj1._state.db in db_list and obj2._state.db in db_list:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # Only allow migrations on the default DB
        if db == 'default':
            return True
        # Never run migrations on Moodle DB
        if db == 'moodle':
            return False
        return None
