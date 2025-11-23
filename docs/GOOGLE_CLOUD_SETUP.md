# Google Cloud Setup para Voice AI Assistant

## ✅ Configuración Completada

Tu proyecto ya está configurado correctamente con Google Cloud Platform. Aquí tienes un resumen de lo que se ha configurado:

### 📋 Información del Proyecto

- **Proyecto ID**: `powerful-outlet-477200-f0`
- **Región**: `us-central1`
- **Cuenta**: `fotero.solidcore@gmail.com`

### 🔑 Credenciales Configuradas

- **Cuenta de Servicio**: `voice-ai-assistant@powerful-outlet-477200-f0.iam.gserviceaccount.com`
- **Archivo de Credenciales**: `voice-ai-service-account-key.json`
- **Roles Asignados**:
  - `roles/aiplatform.admin` - Para usar Vertex AI
  - `roles/aiplatform.user` - Para operaciones básicas
  - `roles/speech.client` - Para Speech API

### 🚀 APIs Habilitadas

- ✅ Vertex AI API (`aiplatform.googleapis.com`)
- ✅ Speech API (`speech.googleapis.com`)

### ⚙️ Configuración del Entorno

El archivo `.env` contiene:

```bash
GOOGLE_APPLICATION_CREDENTIALS=voice-ai-service-account-key.json
GOOGLE_CLOUD_PROJECT=powerful-outlet-477200-f0
VERTEX_AI_REGION=us-central1
VERTEX_AI_MODEL=gemini-2.0-flash-exp
VERTEX_AI_VOICE=Puck
MAX_CONCURRENT_SESSIONS=10
SESSION_TIMEOUT_MINUTES=30
MAX_RESPONSE_LATENCY_MS=300
```

## 🧪 Verificar la Configuración

### 1. Probar Credenciales
```bash
python test_credentials.py
```

### 2. Ejecutar Demo
```bash
python examples/voice_orchestration_demo.py
```

### 3. Ejecutar Tests
```bash
python -m pytest tests/ -v
```

## 🔧 Comandos Útiles de gcloud

### Verificar configuración actual:
```bash
gcloud config list
```

### Ver cuentas de servicio:
```bash
gcloud iam service-accounts list
```

### Ver roles asignados:
```bash
gcloud projects get-iam-policy powerful-outlet-477200-f0
```

### Regenerar clave de servicio (si es necesario):
```bash
gcloud iam service-accounts keys create new-key.json \
  --iam-account=voice-ai-assistant@powerful-outlet-477200-f0.iam.gserviceaccount.com
```

## 🚨 Seguridad

### ⚠️ Importante:
- **NO** subas el archivo `voice-ai-service-account-key.json` a Git
- **NO** compartas las credenciales públicamente
- El archivo ya está en `.gitignore`

### 🔒 Buenas Prácticas:
- Rota las claves regularmente
- Usa roles con permisos mínimos necesarios
- Monitorea el uso de las APIs en Google Cloud Console

## 💰 Monitoreo de Costos

### Ver uso actual:
1. Ve a [Google Cloud Console](https://console.cloud.google.com)
2. Selecciona el proyecto `powerful-outlet-477200-f0`
3. Ve a "Billing" > "Cost breakdown"

### APIs que generan costos:
- **Vertex AI Live API**: Por minuto de conversación
- **Speech API**: Por minuto de audio procesado
- **Vertex AI Models**: Por token procesado

## 🆘 Solución de Problemas

### Error de autenticación:
```bash
# Re-autenticar
gcloud auth login fotero.solidcore@gmail.com
gcloud auth application-default login
```

### Error de permisos:
```bash
# Verificar roles
gcloud projects get-iam-policy powerful-outlet-477200-f0 \
  --flatten="bindings[].members" \
  --filter="bindings.members:voice-ai-assistant@*"
```

### Error de proyecto:
```bash
# Cambiar proyecto
gcloud config set project powerful-outlet-477200-f0
```

## 📞 Soporte

Si tienes problemas:

1. Verifica que el proyecto tenga créditos disponibles
2. Revisa que las APIs estén habilitadas
3. Confirma que la cuenta de servicio tenga los roles correctos
4. Ejecuta `python test_credentials.py` para diagnosticar

## 🎉 ¡Listo para Usar!

Tu configuración está completa. Ahora puedes:

1. **Desarrollar**: Usar las APIs de Vertex AI en tu código
2. **Probar**: Ejecutar los ejemplos y tests
3. **Desplegar**: Tu aplicación está lista para producción

¡Disfruta construyendo tu asistente de voz con IA! 🚀