# utils/bedrock_client.py
import os, json, re, base64, boto3
from typing import Dict, Any, Optional, Tuple, List
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError

INFERENCE_PROFILE_PROVIDERS = (
    "anthropic.", "amazon.nova-", "meta.", "mistral.", "writer.", "twelvelabs.", "deepseek.",
)

def _resolve_model_id_for_profile(model_id: str) -> str:
    mid = (model_id or "").strip()
    if mid.startswith("arn:"):   # ARN de inference profile
        return mid
    if mid.startswith("us."):    # ya es inference profile-id
        return mid
    if any(mid.startswith(p) for p in INFERENCE_PROFILE_PROVIDERS):
        return f"us.{mid}"       # modelId → profileId
    return mid

class BedrockClient:
    def __init__(self, model_id: str, region: str = "us-east-1"):
        self.original_model_id = model_id
        self.resolved_model_id = _resolve_model_id_for_profile(model_id)

        if not os.getenv('AWS_ACCESS_KEY_ID') or not os.getenv('AWS_SECRET_ACCESS_KEY'):
            raise ValueError("AWS credentials not found in env. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")

        cfg = Config(connect_timeout=60, read_timeout=300, retries={"max_attempts": 3, "mode": "standard"})
        try:
            self.client = boto3.client(
                "bedrock-runtime",
                region_name=region,
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                aws_session_token=os.getenv("AWS_SESSION_TOKEN", None),
                config=cfg
            )
        except NoCredentialsError:
            raise ValueError("AWS credentials are invalid or not properly configured")

    # -------------------- Public --------------------

    def analyze_compliance(
        self,
        planogram_b64: str,
        realogram_b64: str,
        prompt: str,
        json_structure: Dict,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> Dict:
        provider = self._provider_from_id(self.original_model_id)

        if provider == "anthropic":
            body = self._build_anthropic(planogram_b64, realogram_b64, prompt, temperature, max_tokens)
        elif provider == "nova":
            body = self._build_nova(planogram_b64, realogram_b64, prompt, temperature, max_tokens)
        elif provider == "meta":
            body = self._build_llama(planogram_b64, realogram_b64, prompt, temperature, max_tokens)
        else:
            body = self._build_generic(planogram_b64, realogram_b64, prompt, temperature, max_tokens)

        try:
            try:
                resp = self.client.invoke_model(
                    modelId=self.resolved_model_id,
                    body=json.dumps(body),
                    contentType="application/json",
                    accept="application/json",
                )
            except ClientError as e:
                raise self._map_error(e)

            payload = json.loads(resp["body"].read())
            text = self._extract_text(payload, provider) or ""
            text = self._strip_fences(text)

            # 1) parse directo
            parsed = self._try_parse_json(text)

            # 2) si no parsea, extraer primer bloque JSON del texto
            if parsed is None:
                parsed = self._extract_first_json_object(text)

            if parsed is None:
                return self._err_parse(text, json_structure)

            # 3) si ya trae 'diferencias', devolver tal cual
            if isinstance(parsed, dict) and "diferencias" in parsed:
                parsed["_debug"] = self._debug()
                return parsed

            # 4) normalizar si vino como 'gondola'/'niveles'
            normalized = self._normalize_gondola_schema(parsed)
            if normalized and "diferencias" in normalized:
                normalized["_debug"] = self._debug()
                return normalized

            # 5) normalizar si vino como 'productos' plano
            normalized2 = self._normalize_flat_products_schema(parsed)
            if normalized2 and "diferencias" in normalized2:
                normalized2["_debug"] = self._debug()
                return normalized2

            # 6) último recurso: error estructurado con raw
            return {
                "error": "Response missing 'diferencias' field",
                "raw_response": text,
                "diferencias": json_structure.get("diferencias", []),
                "conclusiones": ["Error: El modelo no devolvió la estructura esperada"],
                "_debug": self._debug(),
            }

        except Exception as e:
            return {
                "error": str(e),
                "diferencias": json_structure.get("diferencias", []),
                "conclusiones": [f"Error en el análisis: {str(e)}"],
                "_debug": self._debug(),
            }

    # -------------------- Builders --------------------

    def _build_anthropic(self, p64: str, r64: str, prompt: str, temp: float, max_tok: int) -> Dict:
        # Claude (Anthropic) multimodal (Bedrock)
        return {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tok,
            "temperature": temp,
            "top_p": 0.9,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Imagen 1 - PLANOGRAMA (disposición esperada de productos):"},
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": p64}},
                    {"type": "text", "text": "Imagen 2 - REALOGRAMA (disposición actual/real de productos):"},
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": r64}},
                    {"type": "text", "text": prompt},
                ],
            }],
        }

    def _build_nova(self, p64: str, r64: str, prompt: str, temp: float, max_tok: int) -> Dict:
        """
        Amazon Nova (messages-v1) correcto:
        - Bloques de texto con 'inputText'
        - Imágenes bajo 'image': {'format','source':{'bytes':<base64>}}
        """
        return {
            "schemaVersion": "messages-v1",
            "messages": [{
                "role": "user",
                "content": [
                    {"inputText": "Imagen 1 - PLANOGRAMA (disposición esperada de productos):"},
                    {"image": {"format": "jpeg", "source": {"bytes": p64}}},
                    {"inputText": "Imagen 2 - REALOGRAMA (disposición actual/real de productos):"},
                    {"image": {"format": "jpeg", "source": {"bytes": r64}}},
                    {"inputText": prompt},
                ],
            }],
            "inferenceConfig": {"maxTokens": max_tok, "temperature": temp, "topP": 0.9, "topK": 50},
        }

    def _build_llama(self, p64: str, r64: str, prompt: str, temp: float, max_tok: int) -> Dict:
        # Tu payload heredado para Llama Vision
        return {"prompt": prompt, "images": [p64, r64], "max_gen_len": max_tok, "temperature": temp, "top_p": 0.9}

    def _build_generic(self, p64: str, r64: str, prompt: str, temp: float, max_tok: int) -> Dict:
        # Fallback messages-v1 (acepta inputText/image)
        return {
            "schemaVersion": "messages-v1",
            "messages": [{
                "role": "user",
                "content": [
                    {"inputText": "Imagen 1 - PLANOGRAMA (disposición esperada de productos):"},
                    {"image": {"format": "jpeg", "source": {"bytes": p64}}},
                    {"inputText": "Imagen 2 - REALOGRAMA (disposición actual/real de productos):"},
                    {"image": {"format": "jpeg", "source": {"bytes": r64}}},
                    {"inputText": prompt},
                ],
            }],
            "inferenceConfig": {"maxTokens": max_tok, "temperature": temp, "topP": 0.9},
        }

    # -------------------- Parsing helpers --------------------

    def _extract_text(self, payload: Dict[str, Any], provider: str) -> Optional[str]:
        # Anthropic (Bedrock) → {"content":[{"text":"..."}]}
        if "content" in payload and isinstance(payload["content"], list):
            return "\n".join([b.get("text", "") for b in payload["content"] if isinstance(b, dict) and "text" in b]) or None
        # Llama heredado → {"generation":"..."}
        if "generation" in payload:
            return payload.get("generation")
        # messages-v1 → prefer "output.message.content[].text" o "outputText"
        out = payload.get("output", {})
        if "message" in out:
            blocks = out["message"].get("content", [])
            texts = []
            for b in blocks:
                # Nova puede usar 'text' o 'outputText' según ruta
                if isinstance(b, dict) and "text" in b:
                    texts.append(b["text"])
            if texts:
                return "\n".join(texts)
        if "outputText" in out:
            return out.get("outputText")
        # fallback
        return json.dumps(payload, ensure_ascii=False)

    def _strip_fences(self, s: str) -> str:
        s = s.strip()
        if "```json" in s:
            s = s.split("```json", 1)[-1]
        if "```" in s:
            s = s.replace("```", "")
        return s.strip()

    def _try_parse_json(self, s: str) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(s)
        except Exception:
            return None

    def _extract_first_json_object(self, s: str) -> Optional[Dict[str, Any]]:
        start = s.find("{")
        end = s.rfind("}")
        if start != -1 and end != -1 and end > start:
            snippet = s[start:end+1]
            try:
                return json.loads(snippet)
            except Exception:
                return None
        return None

    # ---- Normalización A: gondola → diferencias ----
    def _normalize_gondola_schema(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        gondola = data.get("gondola") or {}
        niveles = gondola.get("niveles")
        if not isinstance(niveles, list):
            return None

        difs: List[Dict[str, Any]] = []
        for niv in niveles:
            nivel_id = niv.get("nivel")
            try:
                # E2 → 2; "1" → 1
                if isinstance(nivel_id, str):
                    nivel_id = int(re.sub(r"[^0-9]", "", nivel_id)) if re.search(r"\d", nivel_id) else nivel_id
            except Exception:
                pass

            prods = niv.get("productos", [])
            out_prods = []
            for p in prods:
                nombre_base = p.get("nombre", "") or ""
                tipo = p.get("tipo") or p.get("clase") or p.get("envase")
                tam = p.get("tamano") or p.get("tamaño") or p.get("tam")
                nombre = nombre_base
                if tipo or tam:
                    nombre = " ".join([x for x in [nombre_base, tipo, tam] if x])

                out_prods.append({
                    "posicion_producto": p.get("posicion") or p.get("posicion_producto") or 1,
                    "nombre": nombre,
                    "encontrado": p.get("encontrado"),
                    "posicion_correcta": p.get("posicion_correcta"),
                    "frentes_esperados": p.get("frentes_esperados") or p.get("frentes_planogramados"),
                    "frentes_encontrados": p.get("frentes_encontrados", 0),
                })

            difs.append({"nivel": nivel_id, "resultado": {"productos": out_prods}})

        conclusiones: List[str] = []
        anom = data.get("anomalias_detectadas", {})
        if isinstance(anom, dict):
            for v in anom.values():
                if isinstance(v, list):
                    conclusiones.extend([s for s in v if isinstance(s, str)])
        recs = data.get("recomendaciones", [])
        if isinstance(recs, list):
            conclusiones.extend([r for r in recs if isinstance(r, str)])
        met = data.get("metricas_cumplimiento")
        if isinstance(met, dict) and met:
            conclusiones.append(f"Métricas de cumplimiento: {json.dumps(met, ensure_ascii=False)}")

        return {"diferencias": difs, "conclusiones": conclusiones}

    # ---- Normalización B: productos[] plano → diferencias ----
    def _normalize_flat_products_schema(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        productos = data.get("productos")
        if not isinstance(productos, list):
            return None

        # agrupar por nivel
        by_level: Dict[Any, List[Dict[str, Any]]] = {}
        for p in productos:
            nivel = p.get("nivel")
            try:
                if isinstance(nivel, str):
                    nivel = int(re.sub(r"[^0-9]", "", nivel)) if re.search(r"\d", nivel) else nivel
            except Exception:
                pass
            by_level.setdefault(nivel, []).append(p)

        difs: List[Dict[str, Any]] = []
        for nivel, plist in sorted(by_level.items(), key=lambda kv: (isinstance(kv[0], int), kv[0])):
            out_prods = []
            for p in plist:
                marca = p.get("marca")
                tipo = p.get("tipo") or p.get("clase") or p.get("envase")
                envase = p.get("envase")
                tam = p.get("tamano") or p.get("tamaño")
                # armar nombre
                nombre = " ".join([x for x in [marca, tipo, envase, tam] if x]) if marca else p.get("nombre", "")
                out_prods.append({
                    "posicion_producto": p.get("posicion") or p.get("posicion_producto") or 1,
                    "nombre": nombre or "Producto",
                    "encontrado": p.get("encontrado"),
                    "posicion_correcta": p.get("posicion_correcta"),
                    "frentes_esperados": p.get("frentes_planogramados") or p.get("frentes_esperados"),
                    "frentes_encontrados": p.get("frentes_encontrados", 0),
                })
            difs.append({"nivel": nivel, "resultado": {"productos": out_prods}})

        conclusiones: List[str] = []
        if isinstance(data.get("productos_no_planogramados"), list):
            for it in data["productos_no_planogramados"]:
                if isinstance(it, dict):
                    desc = it.get("descripcion") or json.dumps(it, ensure_ascii=False)
                    conclusiones.append(f"No planogramados: {desc}")
        if "porcentaje_cumplimiento" in data:
            conclusiones.append(f"Porcentaje de cumplimiento reportado: {data['porcentaje_cumplimiento']}")
        if "observaciones" in data and isinstance(data["observaciones"], str):
            conclusiones.append(data["observaciones"])

        return {"diferencias": difs, "conclusiones": conclusiones}

    # -------------------- Miscs --------------------

    def _provider_from_id(self, model_id: str) -> str:
        mid = (model_id or "").lower()
        if "anthropic" in mid or "claude" in mid:
            return "anthropic"
        if "amazon.nova" in mid or "nova-" in mid:
            return "nova"
        if "llama" in mid or "meta." in mid:
            return "meta"
        return "generic"

    def _map_error(self, e: ClientError) -> ValueError:
        code = e.response.get("Error", {}).get("Code", "Unknown")
        msg = e.response.get("Error", {}).get("Message", "")
        region = getattr(self.client.meta, "region_name", "unknown")

        if "isn’t supported" in msg or "isn't supported" in msg:
            hint = ("Este modelo requiere Inference Profile. Usa 'us.<model_id>' o un ARN de profile. "
                    "Invoca desde us-east-1/us-east-2/us-west-2 (cross-Region soportado).")
            return ValueError(f"Validation Error: {msg} [region={region}]. {hint}")
        if code == "UnrecognizedClientException":
            return ValueError(f"AWS Authentication Error: {msg}. Verifica credenciales.")
        if code == "AccessDeniedException":
            return ValueError(f"Access Denied: {msg}. Revisa permisos en Bedrock / profile.")
        if code == "ValidationException":
            return ValueError(f"Validation Error: {msg}.")
        if code == "ResourceNotFoundException":
            return ValueError(f"Model/Profile not found: {msg}.")
        return ValueError(f"AWS Error ({code}): {msg}")

    def _err_parse(self, raw: str, json_structure: Dict) -> Dict:
        return {
            "error": "Could not parse JSON response",
            "raw_response": raw,
            "diferencias": json_structure.get("diferencias", []),
            "conclusiones": ["Error: No se pudo parsear la respuesta del modelo como JSON"],
            "_debug": self._debug(),
        }

    def _debug(self) -> Dict[str, Any]:
        return {
            "original_model_id": self.original_model_id,
            "resolved_model_id": self.resolved_model_id,
            "region": getattr(self.client.meta, "region_name", None),
        }
