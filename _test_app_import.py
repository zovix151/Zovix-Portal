import os
import streamlit as st
import tornado.web

# 1. Streamlit ke internal Tornado server me static files ka route register karna
try:
    from streamlit.web.server.server import Server

    # Static files path (Zovix-Clean/static directory)
    static_path = os.path.join(os.path.dirname(__file__), "static")

    # Current running instance get karna
    server = Server.get_current()
    if server and hasattr(server, "_tornado_app") and server._tornado_app:
        app = server._tornado_app

        # Plain text routes inject karna
        routes = [
            (
                r"/robots\.txt",
                tornado.web.StaticFileHandler,
                {"path": os.path.join(static_path, "robots.txt")},
            ),
            (
                r"/sitemap\.xml",
                tornado.web.StaticFileHandler,
                {"path": os.path.join(static_path, "sitemap.xml")},
            ),
        ]
        app.add_handlers(r".*", routes)
except Exception as e:
    pass