from bson import ObjectId
from rest_framework import serializers

from utils.messages import messages


class ObjectIdField(serializers.CharField):
    def to_internal_value(self, data):
        value = super().to_internal_value(data).strip()

        if not ObjectId.is_valid(value):
            raise serializers.ValidationError(messages["invalidTenantId"])

        return ObjectId(value)
