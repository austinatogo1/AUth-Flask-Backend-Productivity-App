"""Marshmallow schemas.

These are the boundary between the database and the outside world. A field that
is absent here can never be serialized into a response, which is the second
layer of protection on the password hash.
"""

from marshmallow import EXCLUDE, Schema, fields, validate

from models import JournalEntry, User


class UserSchema(Schema):
    """Serializes a User. There is deliberately no password field of any kind."""

    class Meta:
        unknown = EXCLUDE

    id = fields.Int(dump_only=True)
    username = fields.Str(
        required=True,
        validate=validate.Length(min=User.MIN_USERNAME_LENGTH, max=50),
    )
    created_at = fields.DateTime(dump_only=True)


class JournalEntrySchema(Schema):
    """Serializes and validates a JournalEntry.

    user_id is dump_only, so a client cannot assign an entry to another account
    by including it in the request body. unknown = EXCLUDE drops such fields
    silently rather than rejecting the whole request.
    """

    class Meta:
        unknown = EXCLUDE

    id = fields.Int(dump_only=True)
    title = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=JournalEntry.MAX_TITLE_LENGTH),
    )
    content = fields.Str(required=True, validate=validate.Length(min=1))
    mood = fields.Str(validate=validate.OneOf(JournalEntry.VALID_MOODS))
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    user_id = fields.Int(dump_only=True)


user_schema = UserSchema()
entry_schema = JournalEntrySchema()
entries_schema = JournalEntrySchema(many=True)
