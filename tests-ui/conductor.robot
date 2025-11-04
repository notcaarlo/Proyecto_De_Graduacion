*** Settings ***
| Resource | resources/common.resource
| Suite Setup | Open App To Login
| Suite Teardown | Close All Browsers
| Test Teardown | Logout If Present

*** Test Cases ***
| Conductor: Login y Perfil
| | Login With | ${CONDUCTOR_USER} | ${CONDUCTOR_PASS}
| | Dashboard Or Perfil
| | Page Should Contain | Bienvenido,