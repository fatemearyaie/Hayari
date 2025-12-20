import orjson
from rest_framework.renderers import JSONRenderer


class CustomRenderer(JSONRenderer):
    media_type = "application/json"
    format = "json"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get("response") if renderer_context else None

        if response is not None and response.status_code >= 400:
            formatted = {
                "status": response.status_code,
                "data": data if data is not None else None,
            }
        else:
            formatted = {
                "status": response.status_code if response else 200,
                "data": data,
            }

        if formatted is None:
            return b"null"

        # orjson.dumps returns bytes (no need to .encode())
        return orjson.dumps(formatted)