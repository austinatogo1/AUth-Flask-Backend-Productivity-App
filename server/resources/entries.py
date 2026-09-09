from flask import request
from flask_restful import Resource
from marshmallow import ValidationError
 
from config import db
from models import JournalEntry
from schemas import entries_schema, entry_schema
from utils import get_current_user, login_required
 
DEFAULT_PER_PAGE = 10
MAX_PER_PAGE = 50
 
 
def _parse_pagination_args():
    """Reads and validates ?page and ?per_page.
 
    Returns (page, per_page, None) on success or (None, None, error_response).
    """
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", DEFAULT_PER_PAGE))
    except (TypeError, ValueError):
        return None, None, ({"error": "'page' and 'per_page' must be integers."}, 400)
 
    if page < 1 or per_page < 1:
        return None, None, ({"error": "'page' and 'per_page' must be positive."}, 400)
 
    # server to serialize the entire table.
    return page, min(per_page, MAX_PER_PAGE), None
 
 
def _find_owned_entry(entry_id):
    """Fetches an entry belonging to the current user.
 
    Returns (entry, None) or (None, error_response). Filtering by user_id in the
    query means another user's row is never loaded at all, and a request for it
    is indistinguishable from a request for an entry that does not exist.
    """
    user = get_current_user()
    entry = JournalEntry.query.filter_by(id=entry_id, user_id=user.id).first()
    if not entry:
        return None, ({"error": "Entry not found."}, 404)
    return entry, None
 
 
class EntryList(Resource):
    """GET /entries (paginated) and POST /entries."""
 
    @login_required
    def get(self):
        user = get_current_user()
 
        page, per_page, error = _parse_pagination_args()
        if error:
            return error
 
        pagination = (
            JournalEntry.query.filter_by(user_id=user.id)
            .order_by(JournalEntry.created_at.desc(), JournalEntry.id.desc())
            .paginate(page=page, per_page=per_page, error_out=False)
        )
 
        return {
            "entries": entries_schema.dump(pagination.items),
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total_items": pagination.total,
                "total_pages": pagination.pages,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev,
                "next_page": pagination.next_num,
                "prev_page": pagination.prev_num,
            },
        }, 200
 
    @login_required
    def post(self):
        user = get_current_user()
        data = request.get_json(silent=True) or {}
 
        try:
            validated = entry_schema.load(data)
        except ValidationError as error:
            return {"errors": error.messages}, 422
 
        try:
            # user_id comes from the session, never from the request body.
            entry = JournalEntry(user_id=user.id, **validated)
            db.session.add(entry)
            db.session.commit()
        except ValueError as error:
            db.session.rollback()
            return {"error": str(error)}, 422
 
        return entry_schema.dump(entry), 201
 
 
class EntryById(Resource):
    """GET, PATCH and DELETE for a single entry owned by the requester."""
 
    @login_required
    def get(self, id):
        entry, error = _find_owned_entry(id)
        if error:
            return error
        return entry_schema.dump(entry), 200
 
    @login_required
    def patch(self, id):
        entry, error = _find_owned_entry(id)
        if error:
            return error
 
        data = request.get_json(silent=True) or {}
 
        try:
            # partial=True so a client can send only the fields it wants changed.
            validated = entry_schema.load(data, partial=True)
        except ValidationError as validation_error:
            return {"errors": validation_error.messages}, 422
 
        if not validated:
            return {"error": "No valid fields supplied to update."}, 422
 
        try:
            for attr, value in validated.items():
                setattr(entry, attr, value)
            db.session.commit()
        except ValueError as value_error:
            db.session.rollback()
            return {"error": str(value_error)}, 422
 
        return entry_schema.dump(entry), 200
 
    @login_required
    def delete(self, id):
        entry, error = _find_owned_entry(id)
        if error:
            return error
 
        db.session.delete(entry)
        db.session.commit()
        return {}, 204
 