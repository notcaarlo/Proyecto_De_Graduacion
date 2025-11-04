*** Settings ***
Resource    resources/common.resource
Library     String
Suite Setup     Open App To Login
Suite Teardown  Close All Browsers
*** Test Cases ***
Admin: Login y Crear Vehículo
    # Login
    Login With    ${ADMIN_USER}    ${ADMIN_PASS}
    Page Should Contain    ${TXT_DASH}
    Admin: Go To Gestion Vehiculos
    Capture Page Screenshot    ${SCREEN_DIR}/admin_vehiculos_lista.png

    # Código único
    ${RND}=       Generate Random String    5    [LETTERS][NUMBERS]
    ${CODIGO}=    Set Variable    TEST-${RND}
    Set Test Variable    ${CREATED_CODE}    ${CODIGO}
    Log To Console       Creando vehículo con código: ${CODIGO}

    # Crear
    Admin: Crear Vehiculo En Modal    ${CODIGO}    TEST    TEST    2020    TEST    activo

    # Verificar creación
    Admin: Esperar Fila De Vehiculo    ${CODIGO}

*** Keywords ***
Admin: Teardown Limpio
    Run Keyword And Ignore Error    Logout If Present
    [Teardown]    Logout If Present