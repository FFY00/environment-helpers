import environment_helpers


project = 'environment-helpers'
copyright = '2024, Filipe Laíns'  # noqa: A001
author = 'Filipe Laíns'

version = release = environment_helpers.__version__

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx_autodoc_typehints',
]

intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
}

html_theme = 'furo'
html_title = f'{project} {version}'
