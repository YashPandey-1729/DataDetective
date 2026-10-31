"""Reject oversized bodies before Starlette's multipart parser can spool them to disk."""
from starlette.responses import JSONResponse


class RequestLimitsMiddleware:
    def __init__(self, app):
        self.app = app
        self.active_uploads = 0

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['method'] not in {'POST','PUT','PATCH'} or not scope['path'].startswith('/api/'):
            return await self.app(scope, receive, send)
        path = scope['path']
        upload = path in {'/api/datasets', '/api/images'}
        limit = (15 if path == '/api/datasets' else 5) * 1024 * 1024 + 65536 if upload else 16384
        headers = dict(scope.get('headers', []))
        try:
            length = int(headers.get(b'content-length', b'0'))
            if length < 0: raise ValueError()
        except ValueError:
            return await JSONResponse({'detail':'Invalid Content-Length.'}, status_code=400)(scope,receive,send)
        if length > limit:
            return await JSONResponse({'detail':'Request exceeds upload size limit.'}, status_code=413)(scope,receive,send)
        if upload and self.active_uploads >= 2:
            return await JSONResponse({'detail':'Upload capacity reached. Retry after the current files finish.'}, status_code=429)(scope,receive,send)
        if upload: self.active_uploads += 1
        try:
            body = bytearray()
            while True:
                message = await receive()
                if message['type'] == 'http.disconnect': return
                body.extend(message.get('body',b''))
                if len(body) > limit:
                    return await JSONResponse({'detail':'Request exceeds upload size limit.'}, status_code=413)(scope,receive,send)
                if not message.get('more_body',False): break
            sent = False
            async def replay():
                nonlocal sent
                if not sent:
                    sent = True
                    return {'type':'http.request','body':bytes(body),'more_body':False}
                return await receive()
            return await self.app(scope,replay,send)
        finally:
            if upload: self.active_uploads -= 1
