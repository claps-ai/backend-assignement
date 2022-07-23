# Standard library imports
from json import loads
from json import load
from os import _exists
from os import environ
from datetime import datetime

# Third party imports
from bson import json_util
from bson.objectid import ObjectId
from mongoengine import connect
from mongoengine import Document
from mongoengine import ReferenceField
from mongoengine import DictField
from mongoengine import ListField
from mongoengine import MapField
from mongoengine import EmbeddedDocument as _EmbeddedDocument
from mongoengine import EmbeddedDocumentField
from mongoengine import EmbeddedDocumentListField
from mongoengine import DictField
from mongoengine import signals
from mongoengine import NULLIFY
from mongoengine import DateTimeField as _DateTimeField
from mongoengine import FloatField as _FloatField
from mongoengine import IntField as _IntField
from mongoengine import BooleanField as _BooleanField
from mongoengine import StringField as _StringField
from mongoengine import PointField as _PointField
from flask_restx.fields import DateTime
from flask_restx.fields import Float
from flask_restx.fields import Integer
from flask_restx.fields import List
from flask_restx.fields import Nested
from flask_restx.fields import String
from flask_restx.fields import Boolean
from flask_restx.fields import Raw

from models.query_sets import VideoQuerySet

## EXTRA


class PointField(_PointField):
    class ReturnObject(Raw):
        def format(self, value):
            return value

    marshal = ReturnObject


class DateTimeField(_DateTimeField):
    class ISOFormat(DateTime):
        def format(self, value):
            try:
                if isinstance(value, datetime):
                    return value.isoformat()
                return value.get("$date")
            except ValueError as ve:
                raise MarshallingError(ve)

    marshal = ISOFormat


class ImageField(_StringField):
    class AWSImage(String):
        def format(self, value):
            try:
                return get_presigned_url(value)
            except ValueError as ve:
                raise MarshallingError(ve)

    marshal = AWSImage


class FloatField(_FloatField):
    marshal = Float


class IntField(_IntField):
    marshal = Integer


class BooleanField(_BooleanField):
    marshal = Boolean


class StringField(_StringField):
    marshal = String


user = environ.get("username", "root")
password = environ.get("password", "root")
host = environ.get("host", "127.0.0.1")
database_name = environ.get("DB_NAME", "data")

db = connect(
    database_name,
    username=user,
    password=password,
    host=host,
    authentication_source="admin",
)


def convert(value):
    return ObjectId(value) if ObjectId.is_valid(value) else value


class Base:
    @classmethod
    def base(cls):
        return {
            **{
                key: getattr(cls, key).marshal
                for key, value in list(cls._fields.items())
                if hasattr(getattr(cls, key), "marshal")
            },
            "id": String(),
        }

    @classmethod
    def reference(cls):
        return {
            **cls.base(),
            **{
                field: String()
                for field, instance in cls._fields.items()
                if isinstance(instance, ReferenceField)
            },
        }

    @classmethod
    def model(cls, api):
        return {
            **cls.base(),
            **{
                field: Nested(api.models.get(field), skip_none=True)
                for field, instance in cls._fields.items()
                if isinstance(instance, DictField)
            },
            **{
                field: Nested(
                    api.models.get(instance.document_type_obj._class_name.lower()),
                    skip_none=True,
                )
                for field, instance in cls._embedded_fields().items()
            },
            **{
                field: Nested(
                    api.models.get(instance.document_type._meta["collection"]),
                    skip_none=True,
                )
                for field, instance in cls._reference_fields().items()
            },
            **{
                field: List(
                    Nested(
                        api.models.get(
                            instance.field.document_type._meta["collection"]
                        ),
                        skip_none=True,
                    )
                )
                for field, instance in cls._list_reference_fields().items()
            },
            **{
                field: List(
                    Nested(
                        api.models.get(
                            instance.field.document_type_obj._class_name.lower()
                        )
                    )
                )
                for field, instance in cls._list_embedded_fields().items()
            },
        }

    @classmethod
    def _reference_fields(cls):
        return {
            key: value
            for key, value in cls._fields.items()
            if isinstance(value, ReferenceField)
        }

    @classmethod
    def _embedded_fields(cls):
        return {
            key: value
            for key, value in cls._fields.items()
            if isinstance(value, EmbeddedDocumentField)
        }

    @classmethod
    def _list_reference_fields(cls):
        return {
            key: value
            for key, value in cls._fields.items()
            if isinstance(value, ListField)
            and isinstance(cls._fields[key].field, ReferenceField)
        }

    @classmethod
    def _list_embedded_fields(cls):
        return {
            key: value
            for key, value in cls._fields.items()
            if isinstance(value, EmbeddedDocumentListField)
            and isinstance(cls._fields[key].field, EmbeddedDocumentField)
        }


class Extended(Document, Base):
    meta = {"abstract": True, "allow_inheritance": True}

    @classmethod
    def fix_data(cls, key, value):
        if isinstance(value, list):
            return [cls.fix_data(key, x) for x in value]

        if isinstance(value, str):
            return convert(value)
        elif isinstance(value, dict):
            if "id" in value:
                return convert(value["id"])
            elif isinstance(getattr(cls, key), EmbeddedDocumentField):
                return getattr(cls, key).document_type_obj(**value)
            elif isinstance(getattr(cls, key), EmbeddedDocumentListField):
                return getattr(cls, key).field.document_type_obj(**value)

        else:
            return value

    def to_json(self):
        def f(v):
            if isinstance(v, dict) and "$oid" in v:
                return v["$oid"]
            elif isinstance(v, dict) and "_cls" in v:
                v.pop("_cls")
                return v
            elif isinstance(v, list):
                return list(map(lambda x: f(x), v))
            else:
                return v

        data = {**{k: f(v) for k, v in loads(json_util.dumps(self.to_mongo())).items()}}
        data.pop("_cls")
        data.update({"id": data.pop("_id")})

        return data

    @classmethod
    def load_reference(cls, item):
        if isinstance(item, dict):
            return cls.objects.get(id=item.get("id", cls.post(item)["id"]))

        elif isinstance(item, str):
            cls.objects.get(id=item)

    @classmethod
    def fix_references(cls, data):
        for k, v in cls._reference_fields().items():
            if k in data:
                data.update({k: v.document_type_obj.load_reference(data[k])})

        for k, v in cls._list_reference_fields().items():
            if k in data:
                data[k] = [
                    v.field.document_type_obj.load_reference(item) for item in data[k]
                ]

    @classmethod
    def post(cls, data):
        cls.fix_references(data)
        item = cls(**data)
        item.save()
        return item.to_json()

    @classmethod
    def put(cls, data):
        item = cls.objects.get(id=data.pop("id"))

        [delattr(item, k) for k, v in cls._fields.items() if k not in ["_cls", "id"]]
        for key, value in data.items():
            setattr(item, key, cls.fix_data(key, value))

        item.save()

        return item.to_json()

    @classmethod
    def patch(cls, data):
        item = cls.objects.get(id=data.pop("id"))

        for key, value in data.items():
            setattr(item, key, cls.fix_data(key, value))

        item.save()

        return item.to_json()

    @classmethod
    def get(cls, *args, **kwargs):
        def recursively_query(model, fields, search, root=False):

            if fields == "id__in":
                return {fields: search}

            if "__" not in fields:
                if root:
                    return {fields: search}

                return [x.id for x in model.objects(**{fields: search})]

            prop, fields = fields.split("__", 1)

            result = recursively_query(
                model._fields[prop].field.document_type_obj
                if isinstance(model._fields[prop], ListField)
                else model._fields[prop].document_type_obj,
                fields,
                search,
            )

            if not root:
                return [x.id for x in model.objects(**{"{}__in".format(prop): result})]
            else:
                return {"{}__in".format(prop): result}

        filters = {}
        for query, search in kwargs.items():

            if query.startswith("$"):
                continue

            elif query.split("__")[0] not in cls._reference_fields():
                filters.update({query: search})

            else:
                filters.update(
                    {
                        key: list(set(value) & set(filters.get(key, value)))
                        if isinstance(value, list)
                        else value
                        for key, value in recursively_query(
                            cls, query, search, True
                        ).items()
                    }
                )

        return (
            cls.objects(**filters)
            .order_by(*kwargs.get("$sort", [getattr(cls, "sort_by", None)]))
            .skip(int(kwargs.get("$skip", 0)))
            .limit(int(kwargs.get("$limit", 0)))
        )

    @classmethod
    def qry(cls, filters):
        if "$queryset" in filters:
            return getattr(cls.objects, filters.pop("$queryset"))(cls, filters)

        elif hasattr(cls._meta["queryset_class"], "default"):
            return cls.objects.default(cls, filters)

        else:
            return cls.fetch(filters)

    @classmethod
    def fetch(cls, filters):
        include = filters.pop("$include", "").split(",")
        data = [x.to_json() for x in list(cls.get(**filters))]

        for key, value in cls._list_reference_fields().items():
            if key in include:
                id_lists = list(map(lambda x: x[key], data))
                ids = list(set([item for sublist in id_lists for item in sublist]))

                values = value.field.document_type_obj.fetch(
                    {
                        "$include": ",".join(
                            [
                                x.replace("{}__".format(key), "")
                                for x in include
                                if x.startswith(key)
                            ]
                        ),
                        "id__in": ids,
                    },
                )

                values = {x["id"]: x for x in values}

                for item in data:
                    item.update({key: [values[x] for x in item[key]]})

            else:
                for item in data:
                    item.update({key: [{"id": x} for x in item[key]]})

        for key, value in cls._reference_fields().items():
            if key in include:
                ids = [x.get(key) for x in data if key in x]
                values = value.document_type_obj.fetch(
                    {
                        "$include": ",".join(
                            [
                                x.replace("{}__".format(key), "")
                                for x in include
                                if x.startswith(key)
                            ]
                        ),
                        "id__in": ids,
                    },
                )

                values = {x["id"]: x for x in values}

                for item in data:
                    if key in item and item[key] in values:
                        item[key] = values[item[key]]

            else:
                list(
                    map(
                        lambda x: x.update(
                            {key: ({"id": x.get(key)} if key in x else None)}
                        ),
                        data,
                    )
                )

        return data


class EmbeddedDocument(_EmbeddedDocument, Base):
    meta = {"abstract": True, "allow_inheritance": True}


class Video(Extended):
    meta = {"queryset_class": VideoQuerySet}

    title = StringField()
    thumbnail = StringField()
    gif = StringField()
    video = StringField()
