#!/usr/bin/env python3
"""Motor de scraping multi-sitio con soporte para PriceShoes y Avon"""

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time
import json
import os
from datetime import datetime
import logging
import re
from typing import Dict, List, Any, Optional

# Configurar logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("scraper_engine")


class MultiSiteScraper:
    """Scraper que soporta múltiples sitios web con diferentes estructuras de login"""

    def __init__(self):
        self.site_configs = {
            "priceshoes": {
                "name": "PriceShoes",
                "base_url": "https://www.priceshoes.com/",
                "login_url": "https://www.priceshoes.com/login",
                "login_type": "two_step",  # two_step or single_step
                "selectors": {
                    "login_button": [
                        'button:has-text("Ingresar a mi cuenta")',
                        'a:has-text("Ingresar a mi cuenta")',
                        '[class*="account"]',
                    ],
                    "email": [
                        'input[type="text"]',
                        'input[type="email"]',
                        "#email",
                        '[name="email"]',
                    ],
                    "password": [
                        'input[type="password"]',
                        "#password",
                        '[name="password"]',
                    ],
                    "submit": [
                        'button:has-text("Siguiente")',
                        'button:has-text("Ingresar")',
                        'button[type="submit"]',
                    ],
                    "orders": [
                        ".order-item",
                        ".pedido-item",
                        ".order",
                        ".pedido",
                        '[class*="order"]',
                        '[class*="pedido"]',
                    ],
                    "account_menu": ["Mi Cuenta", "Salir", "Cerrar sesión"],
                },
            },
            "avon": {
                "name": "Avon México",
                "base_url": "https://www.mx.avon.com/",
                "login_url": "https://www.mx.avon.com/REPSuite/loginMain.page",
                "login_type": "single_step",
                "selectors": {
                    "login_button": [
                        'a:has-text("Iniciar sesión")',
                        'a:has-text("Mi cuenta")',
                        '[href*="login"]',
                    ],
                    "email": [
                        'input[name="username"]',
                        'input[id="username"]',
                        'input[type="text"]',
                        "#j_username",
                    ],
                    "password": [
                        'input[name="password"]',
                        'input[id="password"]',
                        'input[type="password"]',
                        "#j_password",
                    ],
                    "submit": [
                        'button[type="submit"]',
                        'input[type="submit"]',
                        'button:has-text("Ingresar")',
                        '[value="Ingresar"]',
                    ],
                    "orders": [
                        ".pedido",
                        ".order-history",
                        '[class*="pedido"]',
                        "table.orders",
                        ".mis-pedidos",
                    ],
                    "account_menu": [
                        "Mi Cuenta",
                        "Mis Pedidos",
                        "Cerrar Sesión",
                        "Mi Espacio",
                    ],
                },
            },
        }

    def detect_site(self, url: str) -> str:
        """Detecta el sitio basado en la URL"""
        if "priceshoes" in url.lower():
            return "priceshoes"
        elif "avon" in url.lower():
            return "avon"
        else:
            # Intentar detectar por dominio
            for site_key, config in self.site_configs.items():
                if config["base_url"] in url:
                    return site_key
            return "unknown"

    def run(self, instructions: Dict, url: str, username: str, password: str) -> Dict:
        """Ejecuta el scraper con detección automática del sitio"""

        # Detectar el sitio
        site_type = self.detect_site(url)
        if site_type == "unknown":
            return {
                "success": False,
                "error": "Sitio no soportado. Por favor usa PriceShoes o Avon.",
                "logs": ["Error: Sitio no reconocido"],
                "screenshots": {},
                "extracted_data": {},
                "timestamp": datetime.now().isoformat(),
            }

        site_config = self.site_configs[site_type]
        logger.info(f"Sitio detectado: {site_config['name']}")

        # Ejecutar el scraper específico del sitio
        return self._run_scraper(instructions, url, username, password, site_config)

    def _handle_popups(self, page, logs: List, screenshots: Dict) -> bool:
        """Maneja popups/modals que puedan aparecer durante la navegación"""
        popup_handled = False

        # Primero manejar el popup de cookies si existe
        cookie_selectors = [
            'button:has-text("aceptar todas las cookies")',
            'button:has-text("Aceptar todas las cookies")',
            'button:has-text("ACEPTAR TODAS LAS COOKIES")',
            'button:has-text("Accept all cookies")',
            "#acceptAllCookies",
            '[id*="accept-cookies"]',
            '[class*="accept-cookies"]',
        ]

        for selector in cookie_selectors:
            try:
                element = page.wait_for_selector(selector, timeout=2000)
                if element and element.is_visible():
                    element.click()
                    logs.append(f"Popup de cookies aceptado: {selector}")
                    popup_handled = True
                    time.sleep(1)
                    break
            except:
                continue

        # Luego manejar otros popups/modals
        popup_selectors = [
            # Botones específicos de Avon
            'button:has-text("ok, entiendo")',
            'button:has-text("Ok, entiendo")',
            'button:has-text("OK, entiendo")',
            'button:has-text("ok entiendo")',
            'button:has-text("Ok entiendo")',
            # Botones de confirmación generales
            'button:has-text("OK ENTENDIDO")',
            'button:has-text("OK Entendido")',
            'button:has-text("ENTENDIDO")',
            'button:has-text("ACEPTAR")',
            'button:has-text("CONTINUAR")',
            'button:has-text("OK")',
            # Selectores por clase/id comunes
            ".modal button.btn-primary",
            ".modal button.btn-success",
            ".modal-footer button:not([data-dismiss])",
            '[class*="modal"] button[class*="primary"]',
            '[class*="modal"] button[class*="confirm"]',
            '[class*="popup"] button[class*="accept"]',
            # Botones de cierre
            'button[aria-label="Close"]',
            'button[aria-label="Cerrar"]',
            ".close-button",
            ".modal-close",
            '[class*="close"]:not(select)',
        ]

        for selector in popup_selectors:
            try:
                element = page.wait_for_selector(selector, timeout=2000)
                if element and element.is_visible():
                    # Capturar screenshot del popup
                    popup_screenshot = f"popup_{datetime.now().strftime('%H%M%S')}.png"
                    page.screenshot(path=popup_screenshot)
                    screenshots[f"popup_handled"] = popup_screenshot

                    # Hacer click
                    element.click()
                    logs.append(f"Popup/modal manejado: {selector}")
                    popup_handled = True
                    time.sleep(1)
                    break
            except:
                continue

        return popup_handled

    def _run_scraper(
        self,
        instructions: Dict,
        url: str,
        username: str,
        password: str,
        site_config: Dict,
    ) -> Dict:
        """Ejecuta el scraper con configuración específica del sitio"""
        logs = []
        screenshots = {}
        extracted_data = {}

        def log(message):
            logger.info(message)
            logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

        log(
            f"🚀 Iniciando scraper para {site_config['name']} con {len(instructions['steps'])} pasos"
        )

        with sync_playwright() as p:
            # Configurar el navegador con opciones optimizadas
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-web-security",
                ],
            )

            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="es-MX",
                timezone_id="America/Mexico_City",
            )

            # Agregar cookies y headers para parecer más humano
            context.add_init_script(
                """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """
            )

            page = context.new_page()

            # Configurar timeout más largo para sitios lentos
            page.set_default_timeout(60000)

            try:
                for i, step in enumerate(instructions["steps"]):
                    action = step["action"]
                    value = step["value"]
                    log(
                        f"📍 Paso {i+1}/{len(instructions['steps'])}: {action} - {value}"
                    )

                    if action == "go_to":
                        # Manejar cookies antes de navegar
                        self._handle_popups(page, logs, screenshots)

                        target_url = (
                            site_config["base_url"] if value == "url_base" else value
                        )
                        page.goto(
                            target_url, wait_until="domcontentloaded", timeout=60000
                        )
                        # Esperar a que la página se estabilice
                        try:
                            page.wait_for_load_state("networkidle", timeout=30000)
                        except:
                            logs.append("Timeout esperando networkidle, continuando...")

                        time.sleep(3)

                        # Manejar popups después de cargar la página
                        self._handle_popups(page, logs, screenshots)

                        log(f"✅ Navegación completada a: {target_url}")

                    elif action in ["login", "complete_login_process"]:
                        log(f"🔐 Iniciando proceso de login para {site_config['name']}")
                        login_success = self._perform_login(
                            page, username, password, site_config, logs, screenshots
                        )

                        if login_success:
                            log("✅ Login completado exitosamente")
                            extracted_data["login_status"] = "success"
                        else:
                            log("❌ Login falló")
                            extracted_data["login_status"] = "failed"

                    elif action == "click":
                        clicked = self._safe_click(page, value, site_config)
                        if clicked:
                            log(f"✅ Click exitoso en: {value}")
                        else:
                            log(f"⚠️ No se pudo hacer click en: {value}")
                        time.sleep(2)

                    elif action == "navigate_to":
                        # Manejar posibles popups antes de navegar
                        self._handle_popups(page, logs, screenshots)

                        navigated = self._navigate_to_section(page, value, site_config)
                        if navigated:
                            log(f"✅ Navegación exitosa a: {value}")
                            # Manejar posibles popups después de navegar
                            time.sleep(2)
                            self._handle_popups(page, logs, screenshots)
                        else:
                            log(f"⚠️ No se pudo navegar a: {value}")
                        time.sleep(3)

                    elif action in ["extract", "extract_all"]:
                        log(f"📊 Extrayendo datos: {value}")
                        extraction_result = self._extract_data(page, value, site_config)
                        extracted_data.update(extraction_result)

                        # Captura post-extracción
                        screenshot_path = f"extraction_{site_config['name']}_{datetime.now().strftime('%H%M%S')}.png"
                        page.screenshot(path=screenshot_path, full_page=True)
                        screenshots["extraccion"] = screenshot_path

                    elif action == "wait":
                        wait_time = int(value) if str(value).isdigit() else 3
                        log(f"⏳ Esperando {wait_time} segundos")
                        time.sleep(wait_time)

                # Captura final
                final_screenshot = f"final_{site_config['name']}_{datetime.now().strftime('%H%M%S')}.png"
                page.screenshot(path=final_screenshot, full_page=True)
                screenshots["estado_final"] = final_screenshot

                return {
                    "success": True,
                    "site": site_config["name"],
                    "logs": logs,
                    "screenshots": screenshots,
                    "extracted_data": extracted_data,
                    "url_final": page.url,
                    "timestamp": datetime.now().isoformat(),
                }

            except Exception as e:
                error_screenshot = f"error_{site_config['name']}_{datetime.now().strftime('%H%M%S')}.png"
                try:
                    page.screenshot(path=error_screenshot)
                    screenshots["error"] = error_screenshot
                except:
                    pass

                log(f"❌ Error general: {str(e)}")

                return {
                    "success": False,
                    "site": site_config["name"],
                    "error": str(e),
                    "logs": logs,
                    "screenshots": screenshots,
                    "extracted_data": extracted_data,
                    "timestamp": datetime.now().isoformat(),
                }

            finally:
                browser.close()

    def _perform_login(
        self,
        page,
        username: str,
        password: str,
        site_config: Dict,
        logs: List,
        screenshots: Dict,
    ) -> bool:
        """Realiza el proceso de login según el tipo de sitio"""
        try:
            # Primero manejar cookies si aparecen antes del login
            self._handle_popups(page, logs, screenshots)

            # Verificar si ya estamos en la página de login
            if site_config["login_url"] not in page.url:
                login_clicked = False
                for selector in site_config["selectors"]["login_button"]:
                    try:
                        page.click(selector, timeout=5000)
                        login_clicked = True
                        logs.append(f"Click en botón de login: {selector}")
                        break
                    except:
                        continue

                if not login_clicked:
                    # Navegar directamente a la URL de login
                    page.goto(
                        site_config["login_url"],
                        wait_until="networkidle",
                        timeout=30000,
                    )
                    logs.append(f"Navegación directa a: {site_config['login_url']}")

                time.sleep(3)

            # Manejar popups que puedan aparecer en la página de login
            self._handle_popups(page, logs, screenshots)

            # Proceso de login según el tipo
            if site_config["login_type"] == "two_step":
                # Login en dos pasos (PriceShoes)
                result = self._two_step_login(
                    page, username, password, site_config, logs, screenshots
                )
            else:
                # Login en un solo paso (Avon)
                result = self._single_step_login(
                    page, username, password, site_config, logs, screenshots
                )

            # Después del login, manejar múltiples popups que puedan aparecer
            if result:
                # Esperar un poco para que aparezcan los popups
                time.sleep(2)

                # Intentar manejar popups múltiples veces (para casos como Avon con 2+ popups)
                for i in range(3):  # Hasta 3 popups en secuencia
                    if not self._handle_popups(page, logs, screenshots):
                        break  # Si no hay más popups, salir
                    time.sleep(1)

            return result

        except Exception as e:
            logs.append(f"Error en login: {str(e)}")
            return False

    def _single_step_login(
        self,
        page,
        username: str,
        password: str,
        site_config: Dict,
        logs: List,
        screenshots: Dict,
    ) -> bool:
        """Login en un solo paso (usuario y contraseña en la misma página)"""
        try:
            # Manejar posibles popups antes de llenar el formulario
            self._handle_popups(page, logs, screenshots)

            # Llenar usuario
            user_filled = False
            for selector in site_config["selectors"]["email"]:
                try:
                    page.wait_for_selector(selector, timeout=5000)
                    page.fill(selector, username, force=True)
                    user_filled = True
                    logs.append(f"Usuario llenado con selector: {selector}")
                    break
                except:
                    continue

            if not user_filled:
                logs.append("No se pudo llenar el campo de usuario")
                return False

            # Llenar contraseña
            pass_filled = False
            for selector in site_config["selectors"]["password"]:
                try:
                    page.wait_for_selector(selector, timeout=5000)
                    page.fill(selector, password, force=True)
                    pass_filled = True
                    logs.append(f"Contraseña llenada con selector: {selector}")
                    break
                except:
                    continue

            if not pass_filled:
                logs.append("No se pudo llenar el campo de contraseña")
                return False

            time.sleep(1)

            # Enviar formulario
            submit_clicked = False
            for selector in site_config["selectors"]["submit"]:
                try:
                    page.click(selector, timeout=5000)
                    logs.append(f"Click en submit: {selector}")
                    submit_clicked = True
                    break
                except:
                    continue

            if not submit_clicked:
                # Intentar presionar Enter si no se pudo hacer click
                try:
                    page.keyboard.press("Enter")
                    logs.append("Formulario enviado con Enter")
                except:
                    logs.append("No se pudo enviar el formulario")

            # Esperar a que se complete el login
            time.sleep(5)

            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except:
                logs.append("Timeout esperando carga después del login")

            # Verificar login exitoso antes de buscar popups
            login_successful = False

            # Verificar por cambio de URL
            if "login" not in page.url.lower():
                logs.append("Login verificado por cambio de URL")
                login_successful = True

            # Si parece que el login fue exitoso, manejar popups
            if login_successful or "avon" in page.url.lower():
                # Para Avon específicamente, manejar múltiples popups
                logs.append("Buscando popups post-login...")

                # Manejar hasta 3 popups en secuencia
                for i in range(3):
                    popup_found = self._handle_popups(page, logs, screenshots)
                    if not popup_found:
                        break
                    time.sleep(2)

                # Después de manejar popups, verificar nuevamente el estado
                page.wait_for_load_state("networkidle", timeout=10000)

            # Verificación final del login
            for indicator in site_config["selectors"]["account_menu"]:
                try:
                    if page.query_selector(f'text="{indicator}"'):
                        logs.append(f"Login verificado: se encontró '{indicator}'")
                        return True
                except:
                    pass

            # Si llegamos aquí y la URL cambió, probablemente el login fue exitoso
            if "login" not in page.url.lower():
                return True

            return False

        except Exception as e:
            logs.append(f"Error en single-step login: {str(e)}")
            return False

    def _two_step_login(
        self,
        page,
        username: str,
        password: str,
        site_config: Dict,
        logs: List,
        screenshots: Dict,
    ) -> bool:
        """Login en dos pasos (primero email, luego contraseña)"""
        try:
            # Paso 1: Email
            email_filled = False
            for selector in site_config["selectors"]["email"]:
                try:
                    page.wait_for_selector(selector, timeout=5000)
                    page.fill(selector, username, force=True)
                    email_filled = True
                    logs.append(f"Email llenado con selector: {selector}")
                    break
                except:
                    continue

            if not email_filled:
                logs.append("No se pudo llenar el campo de email")
                return False

            # Click en siguiente
            for selector in site_config["selectors"]["submit"]:
                try:
                    page.click(selector, timeout=5000)
                    logs.append(f"Click en siguiente: {selector}")
                    break
                except:
                    continue

            time.sleep(3)

            # Paso 2: Contraseña
            pass_filled = False
            for selector in site_config["selectors"]["password"]:
                try:
                    page.wait_for_selector(selector, timeout=5000)
                    page.fill(selector, password, force=True)
                    pass_filled = True
                    logs.append(f"Contraseña llenada con selector: {selector}")
                    break
                except:
                    continue

            if not pass_filled:
                logs.append("No se pudo llenar el campo de contraseña")
                return False

            # Click final
            for selector in site_config["selectors"]["submit"]:
                try:
                    page.click(selector, timeout=5000)
                    logs.append(f"Click final en: {selector}")
                    break
                except:
                    continue

            # Esperar y verificar
            time.sleep(5)
            page.wait_for_load_state("networkidle", timeout=30000)

            # Verificar login exitoso
            for indicator in site_config["selectors"]["account_menu"]:
                try:
                    if page.query_selector(f'text="{indicator}"'):
                        logs.append(f"Login verificado: se encontró '{indicator}'")
                        return True
                except:
                    pass

            return "login" not in page.url.lower()

        except Exception as e:
            logs.append(f"Error en two-step login: {str(e)}")
            return False

    def _safe_click(self, page, target: str, site_config: Dict) -> bool:
        """Realiza un click de forma segura con múltiples estrategias"""
        selectors = [
            f'button:has-text("{target}")',
            f'a:has-text("{target}")',
            f'text="{target}"',
            f'[title*="{target}" i]',
            f'[aria-label*="{target}" i]',
            f'*:has-text("{target}")',
        ]

        for selector in selectors:
            try:
                element = page.wait_for_selector(selector, timeout=3000)
                if element:
                    element.scroll_into_view_if_needed()
                    element.click()
                    return True
            except:
                continue

        return False

    def _navigate_to_section(self, page, section: str, site_config: Dict) -> bool:
        """Navega a una sección específica del sitio"""
        # Mapeo de secciones comunes con variaciones por sitio
        section_mappings = {
            "Mis Pedidos": {
                "general": ["pedidos", "orders", "historial", "compras"],
                "avon": ["mis-pedidos", "historial-pedidos", "pedidos-realizados"],
            },
            "Mi Cuenta": {
                "general": ["cuenta", "account", "perfil", "profile"],
                "avon": ["mi-espacio", "mi-cuenta", "datos-personales"],
            },
            "Mis Direcciones": {
                "general": ["direcciones", "address", "domicilio"],
                "avon": ["direcciones-entrega", "mis-direcciones"],
            },
            "Mis Favoritos": {
                "general": ["favoritos", "wishlist", "guardados"],
                "avon": ["favoritos", "productos-favoritos"],
            },
        }

        # Detectar el sitio actual
        site_name = "avon" if "avon" in page.url.lower() else "general"

        # Generar selectores basados en el nombre de la sección
        selectors = [
            f'a:has-text("{section}")',
            f'button:has-text("{section}")',
            f'[href*="{section.lower().replace(" ", "-")}"]',
            f'[href*="{section.lower().replace(" ", "")}"]',
            f'span:has-text("{section}")',
            f'div:has-text("{section}"):not(:has(div))',  # Evitar divs contenedores
        ]

        # Agregar selectores para variaciones del nombre
        for key, mappings in section_mappings.items():
            if key.lower() in section.lower() or section.lower() in key.lower():
                # Agregar variaciones generales
                for var in mappings.get("general", []):
                    selectors.extend(
                        [
                            f'a[href*="{var}"]',
                            f'a:has-text("{var}")',
                            f'[class*="{var}"]',
                        ]
                    )
                # Agregar variaciones específicas del sitio
                if site_name in mappings:
                    for var in mappings[site_name]:
                        selectors.extend(
                            [
                                f'a[href*="{var}"]',
                                f'a:has-text("{var}")',
                                f'[class*="{var}"]',
                            ]
                        )

        # Para Avon, agregar selectores específicos del menú
        if "avon" in page.url.lower():
            selectors.extend(
                [
                    '.menu-item a:has-text("' + section + '")',
                    '.nav-link:has-text("' + section + '")',
                    '[class*="menu"] a:has-text("' + section + '")',
                ]
            )

        # Intentar hacer click en cada selector
        for selector in selectors:
            try:
                element = page.wait_for_selector(selector, timeout=3000)
                if element and element.is_visible():
                    element.scroll_into_view_if_needed()
                    element.click()
                    time.sleep(2)

                    # Verificar si cambió la URL o el contenido
                    page.wait_for_load_state("networkidle", timeout=10000)
                    return True
            except:
                continue

        # Si no se encontró la sección, intentar buscar en menús desplegables
        try:
            # Buscar y abrir menús
            menu_selectors = [
                'button:has-text("Mi Cuenta")',
                'button:has-text("Mi Espacio")',
                '[class*="dropdown"]',
                '[class*="menu-toggle"]',
            ]

            for menu_selector in menu_selectors:
                try:
                    menu = page.wait_for_selector(menu_selector, timeout=2000)
                    if menu:
                        menu.click()
                        time.sleep(1)

                        # Intentar encontrar la sección en el menú abierto
                        for selector in selectors[:5]:  # Solo los primeros selectores
                            try:
                                element = page.wait_for_selector(selector, timeout=2000)
                                if element and element.is_visible():
                                    element.click()
                                    return True
                            except:
                                continue
                except:
                    continue
        except:
            pass

        return False

    def _extract_data(self, page, target: str, site_config: Dict) -> Dict:
        """Extrae datos según el tipo solicitado"""
        extracted = {}

        try:
            if target in ["body", "all"]:
                # Extraer todo el contenido
                content = page.inner_text("body")
                extracted["contenido_completo"] = content
                extracted["resumen"] = (
                    content[:500] + "..." if len(content) > 500 else content
                )

            elif target == "pedidos":
                # Extraer información de pedidos
                pedidos = self._extract_orders(page, site_config)
                extracted["pedidos"] = pedidos
                extracted["total_pedidos"] = len(pedidos)

            elif target == "table":
                # Extraer tablas
                tables = self._extract_tables(page)
                extracted["tablas"] = tables
                extracted["total_tablas"] = len(tables)

            elif target == "cuenta":
                # Extraer información de cuenta
                account_info = self._extract_account_info(page, site_config)
                extracted["informacion_cuenta"] = account_info

            else:
                # Intentar extraer por selector específico
                try:
                    elements = page.query_selector_all(target)
                    texts = [
                        elem.inner_text().strip()
                        for elem in elements
                        if elem.inner_text().strip()
                    ]
                    extracted["elementos_especificos"] = texts
                    extracted["total_elementos"] = len(texts)
                except:
                    # Fallback a contenido general
                    content = page.inner_text('main, [role="main"], body')
                    extracted["contenido"] = (
                        content[:2000] + "..." if len(content) > 2000 else content
                    )

        except Exception as e:
            extracted["error"] = f"Error en extracción: {str(e)}"

        return extracted

    def _extract_orders(self, page, site_config: Dict) -> List[Dict]:
        """Extrae información de pedidos de forma inteligente"""
        orders = []

        # Manejar posibles popups antes de extraer
        self._handle_popups(page, [], {})

        # Esperar a que la página cargue completamente
        page.wait_for_load_state("networkidle", timeout=10000)
        time.sleep(2)

        # Intentar con selectores específicos del sitio
        for selector in site_config["selectors"]["orders"]:
            try:
                order_elements = page.query_selector_all(selector)
                if order_elements:
                    for elem in order_elements:
                        order_data = self._parse_order_element(elem)
                        if order_data:
                            orders.append(order_data)
                    if orders:
                        break
            except:
                continue

        # Si no encontramos pedidos con selectores, buscar en tablas
        if not orders:
            tables = page.query_selector_all("table")
            for table in tables:
                table_text = table.inner_text().lower()
                # Palabras clave más amplias para Avon
                if any(
                    word in table_text
                    for word in [
                        "pedido",
                        "order",
                        "compra",
                        "fecha",
                        "total",
                        "campaña",
                        "folio",
                    ]
                ):
                    table_orders = self._parse_order_table(table)
                    orders.extend(table_orders)

        # Si es Avon, buscar estructura específica
        if "avon" in page.url.lower() and not orders:
            # Avon puede usar estructura diferente
            avon_selectors = [
                ".historial-pedidos",
                ".lista-pedidos",
                '[class*="pedido-item"]',
                ".tabla-pedidos",
                ".detalle-pedido",
            ]

            for selector in avon_selectors:
                try:
                    elements = page.query_selector_all(selector)
                    for elem in elements:
                        order_data = self._parse_avon_order(elem)
                        if order_data:
                            orders.append(order_data)
                except:
                    continue

        # Si aún no hay pedidos, buscar patrones en el texto
        if not orders:
            content = page.inner_text("body")
            orders = self._extract_orders_from_text(content)

        return orders

    def _parse_avon_order(self, element) -> Optional[Dict]:
        """Parsea un pedido específicamente para Avon"""
        try:
            text = element.inner_text()
            order = {}

            # Patrones específicos de Avon
            patterns = {
                "numero_pedido": [
                    r"(?:Folio|Pedido|Número)\s*[:：]?\s*(\d+)",
                    r"(?:C|Campaña)\s*(\d+)",
                    r"#\s*(\d+)",
                ],
                "fecha": [
                    r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
                    r"(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})",
                    r"(?:Fecha|Date)\s*[:：]?\s*([^\n]+)",
                ],
                "total": [
                    r"(?:Total|Monto)\s*[:：]?\s*\$?\s*([\d,]+\.?\d*)",
                    r"\$\s*([\d,]+\.?\d*)",
                    r"([\d,]+\.?\d*)\s*(?:MXN|MX|pesos)",
                ],
                "estado": [
                    r"(?:Estado|Status)\s*[:：]?\s*(\w+)",
                    r"(Entregado|Enviado|Procesando|Cancelado|Pendiente|En proceso)",
                    r"(Facturado|Surtido|Devuelto)",
                ],
                "campana": [
                    r"(?:Campaña|Campaign)\s*[:：]?\s*(\d+)",
                    r"C(\d+)",
                    r"Camp\.\s*(\d+)",
                ],
            }

            # Buscar cada campo
            for field, field_patterns in patterns.items():
                for pattern in field_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        order[field] = match.group(1).strip()
                        break

            # Solo retornar si encontramos al menos algún dato
            if order:
                order["texto_completo"] = (
                    text[:300] + "..." if len(text) > 300 else text
                )
                order["sitio"] = "Avon"
                return order

        except Exception as e:
            logger.error(f"Error parseando pedido de Avon: {e}")

        return None

    def _parse_order_element(self, element) -> Optional[Dict]:
        """Parsea un elemento de pedido individual"""
        try:
            text = element.inner_text()
            order = {}

            # Buscar número de pedido
            order_patterns = [
                r"(?:Pedido|Order|#)\s*[:＃#]?\s*(\d+)",
                r"(?:Número|Number|No\.?)\s*[:＃#]?\s*(\d+)",
                r"(?:ID|Código)\s*[:＃#]?\s*(\w+)",
            ]

            for pattern in order_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    order["numero_pedido"] = match.group(1)
                    break

            # Buscar fecha
            date_patterns = [
                r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
                r"(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})",
                r"(\d{4}[/-]\d{1,2}[/-]\d{1,2})",
            ]

            for pattern in date_patterns:
                match = re.search(pattern, text)
                if match:
                    order["fecha"] = match.group(1)
                    break

            # Buscar total
            total_patterns = [
                r"(?:Total|Monto)\s*[:＄$]?\s*([\d,]+\.?\d*)",
                r"\$\s*([\d,]+\.?\d*)",
                r"([\d,]+\.?\d*)\s*(?:MXN|USD|pesos)",
            ]

            for pattern in total_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    order["total"] = match.group(1)
                    break

            # Buscar estado
            status_patterns = [
                r"(?:Estado|Status)\s*[:：]?\s*(\w+)",
                r"(Entregado|Enviado|Procesando|Cancelado|Pendiente)",
                r"(Delivered|Shipped|Processing|Cancelled|Pending)",
            ]

            for pattern in status_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    order["estado"] = match.group(1)
                    break

            # Solo retornar si encontramos al menos algún dato
            if order:
                order["texto_completo"] = (
                    text[:200] + "..." if len(text) > 200 else text
                )
                return order

        except Exception as e:
            logger.error(f"Error parseando elemento de pedido: {e}")

        return None

    def _parse_order_table(self, table) -> List[Dict]:
        """Parsea una tabla de pedidos"""
        orders = []

        try:
            rows = table.query_selector_all("tr")
            headers = []

            for i, row in enumerate(rows):
                cells = row.query_selector_all("th, td")
                cell_texts = [cell.inner_text().strip() for cell in cells]

                if i == 0 or any(
                    "th" in cell.evaluate("el => el.tagName") for cell in cells
                ):
                    headers = cell_texts
                elif cell_texts and headers:
                    if len(cell_texts) == len(headers):
                        order = {}
                        for header, value in zip(headers, cell_texts):
                            header_lower = header.lower()
                            if any(
                                word in header_lower
                                for word in [
                                    "pedido",
                                    "order",
                                    "número",
                                    "number",
                                    "id",
                                ]
                            ):
                                order["numero_pedido"] = value
                            elif any(
                                word in header_lower for word in ["fecha", "date"]
                            ):
                                order["fecha"] = value
                            elif any(
                                word in header_lower
                                for word in ["total", "monto", "amount"]
                            ):
                                order["total"] = value
                            elif any(
                                word in header_lower for word in ["estado", "status"]
                            ):
                                order["estado"] = value
                            else:
                                order[header] = value

                        if order:
                            orders.append(order)

        except Exception as e:
            logger.error(f"Error parseando tabla de pedidos: {e}")

        return orders

    def _extract_orders_from_text(self, text: str) -> List[Dict]:
        """Extrae pedidos del texto usando patrones"""
        orders = []

        # Dividir el texto en bloques que podrían ser pedidos
        lines = text.split("\n")
        current_order = {}

        for line in lines:
            line = line.strip()
            if not line:
                if current_order:
                    orders.append(current_order)
                    current_order = {}
                continue

            # Buscar patrones de pedido
            if re.search(r"(?:Pedido|Order|#)\s*[:＃#]?\s*\d+", line, re.IGNORECASE):
                if current_order:
                    orders.append(current_order)
                current_order = {"linea": line}

                # Extraer número
                match = re.search(
                    r"(?:Pedido|Order|#)\s*[:＃#]?\s*(\d+)", line, re.IGNORECASE
                )
                if match:
                    current_order["numero_pedido"] = match.group(1)

            # Agregar información al pedido actual
            elif current_order:
                # Buscar fecha
                if re.search(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", line):
                    match = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", line)
                    if match:
                        current_order["fecha"] = match.group(1)

                # Buscar total
                if re.search(r"\$\s*[\d,]+\.?\d*", line):
                    match = re.search(r"\$\s*([\d,]+\.?\d*)", line)
                    if match:
                        current_order["total"] = match.group(1)

        # Agregar el último pedido si existe
        if current_order:
            orders.append(current_order)

        return orders

    def _extract_tables(self, page) -> List[Dict]:
        """Extrae todas las tablas de la página"""
        tables_data = []

        try:
            tables = page.query_selector_all("table")

            for idx, table in enumerate(tables):
                table_info = {"indice": idx, "headers": [], "filas": [], "resumen": ""}

                # Extraer headers
                headers = table.query_selector_all(
                    "thead th, tr:first-child th, tr:first-child td"
                )
                table_info["headers"] = [h.inner_text().strip() for h in headers]

                # Extraer filas
                rows = table.query_selector_all("tbody tr, tr")
                for row in rows[1:]:  # Saltar la primera si ya son headers
                    cells = row.query_selector_all("td")
                    if cells:
                        row_data = [cell.inner_text().strip() for cell in cells]
                        table_info["filas"].append(row_data)

                # Crear resumen
                if table_info["filas"]:
                    table_info[
                        "resumen"
                    ] = f"Tabla con {len(table_info['headers'])} columnas y {len(table_info['filas'])} filas"

                tables_data.append(table_info)

        except Exception as e:
            logger.error(f"Error extrayendo tablas: {e}")

        return tables_data

    def _extract_account_info(self, page, site_config: Dict) -> Dict:
        """Extrae información de la cuenta del usuario"""
        account_info = {}

        try:
            # Buscar información común de cuenta
            info_patterns = {
                "nombre": [r"(?:Nombre|Name)\s*[:：]?\s*([^\n]+)", r"Hola\s+([^\n,]+)"],
                "email": [r"(?:Email|Correo)\s*[:：]?\s*([\w\.-]+@[\w\.-]+)"],
                "telefono": [r"(?:Teléfono|Phone|Tel)\s*[:：]?\s*([\d\s\-\(\)]+)"],
                "id_cliente": [
                    r"(?:ID Cliente|Customer ID|Número de socio)\s*[:：]?\s*(\w+)"
                ],
                "puntos": [r"(?:Puntos|Points)\s*[:：]?\s*([\d,]+)"],
                "nivel": [r"(?:Nivel|Level|Categoría)\s*[:：]?\s*(\w+)"],
            }

            content = page.inner_text("body")

            for field, patterns in info_patterns.items():
                for pattern in patterns:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        account_info[field] = match.group(1).strip()
                        break

            # Buscar elementos específicos con información
            personal_selectors = [
                '[class*="profile"]',
                '[class*="personal"]',
                '[class*="account-info"]',
                ".datos-personales",
                "#account-details",
            ]

            for selector in personal_selectors:
                try:
                    elements = page.query_selector_all(selector)
                    for elem in elements:
                        text = elem.inner_text()
                        if text and len(text) < 1000:  # Evitar bloques muy grandes
                            account_info[f"info_adicional_{selector}"] = text
                except:
                    continue

        except Exception as e:
            logger.error(f"Error extrayendo información de cuenta: {e}")
            account_info["error"] = str(e)

        return account_info


# Función helper para compatibilidad con el código anterior
def run_scraper(instructions: Dict, url: str, username: str, password: str) -> Dict:
    """Función de compatibilidad con la interfaz anterior"""
    scraper = MultiSiteScraper()
    return scraper.run(instructions, url, username, password)
