from bson import ObjectId
from rest_framework import serializers

from utils.messages import messages


class ObjectIdField(serializers.CharField):
    """A tenant id: a real ObjectId, kept exactly as it was given.

    Nothing is derived or padded. An id that is not a 24-character ObjectId
    is refused rather than turned into some other tenant's id quietly.
    """

    def to_internal_value(self, data):
        value = super().to_internal_value(data).strip()

        if not ObjectId.is_valid(value):
            raise serializers.ValidationError(messages["invalidTenantId"])

        return ObjectId(value)
