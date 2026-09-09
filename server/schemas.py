from marshmallow import Schema, fields, validate

from models import JournalEntry


class UserSchema(Schema):
    """Serializes a User. Note that no password field exists here at all."""

    id = fields.Int(dump_only=True)
    username = fields.Str(required=True, validate=validate.Length(min=3, max=50))
    created_at = fields.DateTime(dump_only=True)


class JournalEntrySchema(Schema):
    id = fields.Int(dump_only=True)
    title = fields.Str(required=True, validate=validate.Length(min=1, max=120))
    content = fields.Str(required=True, validate=validate.Length(min=1))
    mood = fields.Str(validate=validate.OneOf(JournalEntry.VALID_MOODS))
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    user_id = fields.Int(dump_only=True)


user_schema = UserSchema()
entry_schema = JournalEntrySchema()
entries_schema = JournalEntrySchema(many=True)