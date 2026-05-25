from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    MAX_AGENT_ITERATIONS=(int, 12),
    MAX_INPUT_TOKENS=(int, 40000),
)

environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])

INSTALLED_APPS = [
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "research",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": env.db("DATABASE_URL"),
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

MEDIA_ROOT = env("MEDIA_ROOT", default=str(BASE_DIR / "media"))
MEDIA_URL = "/media/"

LLM_PROVIDER = env("LLM_PROVIDER", default="openai")
OPENAI_API_KEY = env("OPENAI_API_KEY", default="")
OPENAI_MODEL = env("OPENAI_MODEL", default="gpt-4o")
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY", default="")
ANTHROPIC_MODEL = env("ANTHROPIC_MODEL", default="claude-sonnet-4-6")
OLLAMA_BASE_URL = env("OLLAMA_BASE_URL", default="http://localhost:11434")
OLLAMA_MODEL = env("OLLAMA_MODEL", default="llama3.2")
MAX_AGENT_ITERATIONS: int = env("MAX_AGENT_ITERATIONS")
MAX_INPUT_TOKENS: int = env("MAX_INPUT_TOKENS")

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

JAZZMIN_SETTINGS = {
    "site_title": "Research Agent",
    "site_header": "Codebase Research Agent",
    "site_brand": "Research Agent",
    "site_logo": None,
    "welcome_sign": "Codebase Research Agent — Admin",
    "copyright": "Al Amin Ahamed",
    "search_model": ["research.ResearchSession", "research.Repository"],
    "topmenu_links": [
        {"name": "API Sessions", "url": "/api/sessions/", "new_window": True},
        {"name": "View Site", "url": "/", "new_window": False},
    ],
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": [],
    "hide_models": [],
    "order_with_respect_to": [
        "research",
        "research.ResearchSession",
        "research.Repository",
        "research.ToolCall",
        "research.Finding",
        "auth",
    ],
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.group": "fas fa-users",
        "research.repository": "fas fa-code-branch",
        "research.researchsession": "fas fa-search",
        "research.toolcall": "fas fa-tools",
        "research.finding": "fas fa-lightbulb",
    },
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",
    "related_modal_active": True,
    "show_ui_builder": False,
    "changeform_format": "horizontal_tabs",
    "language_chooser": False,
    "custom_css": "admin/css/admin_theme.css",
    "custom_js": None,
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-dark",
    "accent": "accent-primary",
    "navbar": "navbar-dark",
    "no_navbar_border": False,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "default",
    "dark_mode_theme": None,
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success",
    },
}
