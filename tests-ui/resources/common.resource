*** Settings ***
Library    SeleniumLibrary
*** Variables ***
${BASE_URL}         http://127.0.0.1:5000
${BROWSER}          chrome
${SCREEN_DIR}       reports/ui
${TIMEOUT}          5s
${SHORT}            2s
${SPEED}            0.2s

# Credenciales
${CONDUCTOR_USER}   test
${CONDUCTOR_PASS}   test
${ADMIN_USER}       carlo
${ADMIN_PASS}       carlo


${SEL_USER}         css:input[name="username"]
${SEL_PASS}         css:input[name="password"]
${SEL_SUBMIT}       xpath=//button[@type="submit" and normalize-space(.)="Iniciar sesión"]
${TXT_DASH}         Panel de administración
${TXT_PERFIL}       Bienvenido,

# Credenciales de vehhículos
${BTN_NUEVO_VEH}    xpath=//button[@data-bs-target="#modalNuevoVehiculo"]
${INP_CODIGO}       css:input[name="codigo"]
${INP_MARCA}        css:input[name="marca"]
${INP_MODELO}       css:input[name="modelo"]
${INP_ANIO}         css:input[name="anio"]
${INP_PLACA}        css:input[name="placa"]
${SEL_ESTADO}       css:select[name="estado"]

${MODAL_ID}         modalNuevoVehiculo
${BTN_CREAR}        xpath=//div[@id="modalNuevoVehiculo"]//button[normalize-space(.)="Crear"]
${TIMEOUT_MODAL}    10s

*** Keywords ***
Open App To Login
    Open Browser    about:blank    ${BROWSER}
    Set Selenium Timeout    ${TIMEOUT}
    Set Selenium Speed      ${SPEED}
    Maximize Browser Window
    Go To    ${BASE_URL}/login
    Wait Until Element Is Visible    ${SEL_USER}    ${TIMEOUT}
    Wait Until Element Is Visible    ${SEL_PASS}    ${TIMEOUT}
    Capture Page Screenshot          ${SCREEN_DIR}/00_login.png
Go To Login
    Go To    ${BASE_URL}/login
    Wait Until Element Is Visible    ${SEL_USER}    ${TIMEOUT}
Login With
    [Arguments]    ${user}    ${pass}
    Input Text         ${SEL_USER}    ${user}
    Input Password     ${SEL_PASS}    ${pass}
    Click Element      ${SEL_SUBMIT}
Dashboard Or Perfil
    ${on_dash}=      Run Keyword And Return Status    Wait Until Page Contains    ${TXT_DASH}      ${TIMEOUT}
    ${on_perfil}=    Run Keyword And Return Status    Wait Until Page Contains    ${TXT_PERFIL}    ${TIMEOUT}
    IF    ${on_dash} or ${on_perfil}
        Log    Después del login se detectó correctamente la página de destino.
    ELSE
        Capture Page Screenshot    ${SCREEN_DIR}/_post_login_desconocido.png
        Log Source
        Fail    Después del login no se detectó Dashboard ni Perfil.
    END
Logout If Present
    ${has_logout}=    Run Keyword And Return Status    Page Should Contain Element    xpath=//a[contains(@class,"btn-logout") or contains(@href,"logout")]
    IF    ${has_logout}
        Click Element    xpath=//a[contains(@class,"btn-logout") or contains(@href,"logout")]
        Wait Until Element Is Visible    ${SEL_USER}    ${SHORT}
    ELSE
        Go To Login
    END

# ----- Gestión de vehículos -----
Admin: _assert_pagina_vehiculos_lista
    ${any}=    Run Keyword And Return Status    Page Should Contain    Gestión de vehículos
    Run Keyword If    ${any}    Return From Keyword
    ${any}=    Run Keyword And Return Status    Page Should Contain Element    ${BTN_NUEVO_VEH}
    Run Keyword If    ${any}    Return From Keyword
    ${any}=    Run Keyword And Return Status    Page Should Contain Element    css:table#tabla
    Run Keyword If    ${any}    Return From Keyword
    Fail    No se detectaron elementos esperados en la página de gestión de vehículos.
Admin: Go To Gestion Vehiculos
    ${link_by_text}=    Set Variable    xpath=//a[normalize-space(.)="Gestión de vehículos"]
    ${link_ready}=      Run Keyword And Return Status    Wait Until Page Contains Element    ${link_by_text}    2s
    IF    ${link_ready}
        Click Element    ${link_by_text}
        ${ok}=    Run Keyword And Return Status    Wait Until Keyword Succeeds    8s    500ms    Admin: _assert_pagina_vehiculos_lista
        Run Keyword If    ${ok}    Return From Keyword
    END
    Go To    ${BASE_URL}/dashboard/vehiculos
    ${ok}=   Run Keyword And Return Status    Wait Until Keyword Succeeds    8s    500ms    Admin: _assert_pagina_vehiculos_lista
    Run Keyword If    ${ok}    Return From Keyword
    ${any_link}=    Set Variable    xpath=//a[contains(@href,"vehiculo")]
    ${has_any}=     Run Keyword And Return Status    Wait Until Page Contains Element    ${any_link}    2s
    IF    ${has_any}
        ${href}=    Get Element Attribute    ${any_link}    href
        Go To       ${href}
        ${ok}=      Run Keyword And Return Status    Wait Until Keyword Succeeds    8s    500ms    Admin: _assert_pagina_vehiculos_lista
        Run Keyword If    ${ok}    Return From Keyword
    END
    ${loc}=    Get Location
    Capture Page Screenshot    ${SCREEN_DIR}/admin_vehiculos_fail.png
    Fail    No se pudo abrir la página de gestión de vehículos. URL actual: ${loc}

# ----- Crear vehículo -----
Admin: Abrir Modal Nuevo Vehiculo
    ${clicked}=    Run Keyword And Return Status    Click Element    ${BTN_NUEVO_VEH}
    ${modal}=      Set Variable    xpath=//div[@id="${MODAL_ID}" and contains(@class,"show")]
    ${abierto}=    Run Keyword And Return Status    Wait Until Page Contains Element    ${modal}    2s
    IF    not ${abierto}
        Execute JavaScript    return bootstrap.Modal.getOrCreateInstance(document.getElementById('${MODAL_ID}')).show();
        Wait Until Page Contains Element    ${modal}    ${TIMEOUT_MODAL}
    END
    Wait Until Element Is Visible    ${INP_CODIGO}    ${TIMEOUT_MODAL}

Admin: Crear Vehiculo En Modal
    [Arguments]    ${codigo}    ${marca}    ${modelo}    ${anio}    ${placa}    ${estado}=activo
    Admin: Abrir Modal Nuevo Vehiculo
    Input Text                   ${INP_CODIGO}    ${codigo}
    Input Text                   ${INP_MARCA}     ${marca}
    Input Text                   ${INP_MODELO}    ${modelo}
    Input Text                   ${INP_ANIO}      ${anio}
    Input Text                   ${INP_PLACA}     ${placa}
    Select From List By Value    ${SEL_ESTADO}    ${estado}
    Capture Page Screenshot      ${SCREEN_DIR}/modal_vehiculo.png
    Click Element                ${BTN_CREAR}
    Wait Until Page Does Not Contain Element    xpath=//div[@id="${MODAL_ID}" and contains(@class,"show")]    ${TIMEOUT_MODAL}
    Wait Until Keyword Succeeds    10s    500ms    Admin: Esperar Fila De Vehiculo    ${codigo}
    Capture Page Screenshot      ${SCREEN_DIR}/vehiculo_creado.png
Admin: Esperar Fila De Vehiculo
    [Arguments]    ${codigo}
    ${row_xpath}=    Set Variable    //table[@id="tabla"]//tbody//tr[td[2][normalize-space()="${codigo}"]]
    Wait Until Page Contains Element    xpath=(${row_xpath})[1]    ${TIMEOUT}
    Return From Keyword    ${row_xpath}