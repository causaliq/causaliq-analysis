# Replace deprecated matplotlib options

Replace deprecated matplotlib options in @src/causaliq-analysis/plot/* with current capabilities without changing functionality so that the following errors seen during pytest tests are no longer reported:

```plaintext
============================== warnings summary ===============================
venv\py311\Lib\site-packages\matplotlib\_fontconfig_pattern.py:64
  C:\dev\causaliq\causaliq-analysis\venv\py311\Lib\site-packages\matplotlib\_fontconfig_pattern.py:64: PyparsingDeprecationWarning: 'oneOf' deprecated - use 'one_of'
    prop = Group((name + Suppress("=") + comma_separated(value)) | oneOf(_CONSTANTS))

venv\py311\Lib\site-packages\matplotlib\_fontconfig_pattern.py:85
venv\py311\Lib\site-packages\matplotlib\_fontconfig_pattern.py:85
venv\py311\Lib\site-packages\matplotlib\_fontconfig_pattern.py:85
venv\py311\Lib\site-packages\matplotlib\_fontconfig_pattern.py:85
venv\py311\Lib\site-packages\matplotlib\_fontconfig_pattern.py:85
venv\py311\Lib\site-packages\matplotlib\_fontconfig_pattern.py:85
  C:\dev\causaliq\causaliq-analysis\venv\py311\Lib\site-packages\matplotlib\_fontconfig_pattern.py:85: PyparsingDeprecationWarning: 'parseString' deprecated - use 'parse_string'
    parse = parser.parseString(pattern)

venv\py311\Lib\site-packages\matplotlib\_fontconfig_pattern.py:89
venv\py311\Lib\site-packages\matplotlib\_fontconfig_pattern.py:89
venv\py311\Lib\site-packages\matplotlib\_fontconfig_pattern.py:89
venv\py311\Lib\site-packages\matplotlib\_fontconfig_pattern.py:89
venv\py311\Lib\site-packages\matplotlib\_fontconfig_pattern.py:89
venv\py311\Lib\site-packages\matplotlib\_fontconfig_pattern.py:89
  C:\dev\causaliq\causaliq-analysis\venv\py311\Lib\site-packages\matplotlib\_fontconfig_pattern.py:89: PyparsingDeprecationWarning: 'resetCache' deprecated - use 'reset_cache'
    parser.resetCache()

venv\py311\Lib\site-packages\matplotlib\_mathtext.py:45
  C:\dev\causaliq\causaliq-analysis\venv\py311\Lib\site-packages\matplotlib\_mathtext.py:45: PyparsingDeprecationWarning: 'enablePackrat' deprecated - use 'enable_packrat'
    ParserElement.enablePackrat()

tests/functional/test_cli_plot.py: 21 warnings
  C:\dev\causaliq\causaliq-analysis\venv\py311\Lib\site-packages\matplotlib\_mathtext.py:2170: PyparsingDeprecationWarning: 'parseString' deprecated - use 'parse_string'
    result = self._expression.parseString(s)

tests/functional/test_cli_plot.py: 21 warnings
  C:\dev\causaliq\causaliq-analysis\venv\py311\Lib\site-packages\matplotlib\_mathtext.py:2197: PyparsingDeprecationWarning: 'parseString' deprecated - use 'parse_string'
    return self._math_expression.parseString(toks[0][1:-1], parseAll=True)

tests/functional/test_cli_plot.py: 21 warnings
  C:\dev\causaliq\causaliq-analysis\venv\py311\Lib\site-packages\pyparsing\util.py:466: PyparsingDeprecationWarning: 'parseAll' argument is deprecated, use 'parse_all'
    return fn(self, *args, **kwargs)

tests/functional/test_cli_plot.py: 21 warnings
  C:\dev\causaliq\causaliq-analysis\venv\py311\Lib\site-packages\matplotlib\_mathtext.py:2178: PyparsingDeprecationWarning: 'resetCache' deprecated - use 'reset_cache'
    ParserElement.resetCache()

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=============================== tests coverage ================================
```