*** Settings ***
| Resource | resources/common.resource
| Suite Setup | Open App To Login
| Suite Teardown | Close All Browsers
| Test Teardown | Logout If Present

*** Variables ***
| ${USER_BAD} | usuario_no_existe
| ${PASS_BAD} | password_incorrecta

*** Test Cases ***
| Login inválido muestra alerta
| | Login With | ${USER_BAD} | ${PASS_BAD}
| | Wait Until Page Contains Element | xpath=//div[contains(@class,"alert")] | ${TIMEOUT}