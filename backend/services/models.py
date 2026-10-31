"""Cloud Gemini and local Ollama model choices."""
import os

DEFAULT_MODEL = 'gemini-3.5-flash-lite'


def local_model_name():
    return os.getenv('OLLAMA_MODEL', 'gemma4:e4b').strip() or 'gemma4:e4b'


def is_local_model(model):
    return bool(model) and model.startswith('ollama:')


def default_model():
    configured = os.getenv('GEMINI_MODEL', DEFAULT_MODEL).strip() or DEFAULT_MODEL
    name = configured.lower().split('/')[-1]
    return DEFAULT_MODEL if name.startswith('gemma') or is_local_model(configured) else configured


def available_models():
    options = [
        {'id': DEFAULT_MODEL, 'label': 'Gemini 3.5 Flash-Lite · Cloud', 'provider': 'google'},
        {'id': 'ollama:' + local_model_name(), 'label': 'Gemma 4 · Local (Ollama)', 'provider': 'ollama'},
    ]
    configured = default_model()
    if configured not in {option['id'] for option in options}:
        options.insert(0, {'id': configured, 'label': f'Configured Gemini · {configured}', 'provider': 'google'})
    return options
