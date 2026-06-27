from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import asyncio

app = FastAPI()

# Database sementara di memori
device_tokens = {}

class RegisterRequest(BaseModel):
    user_id: str
    token: str

class NotificationPayload(BaseModel):
    user_id: str
    title: str
    message: str

# Fungsi internal untuk mengirim notifikasi ke server Expo
async def send_expo_notification(token: str, title: str, message: str):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://exp.host/--/api/v2/push/send",
            json={
                "to": token,
                "title": title,
                "body": message,
            }
        )
        print(f"DEBUG EXPO RESPONSE: {resp.status_code} - {resp.json()}")
        

    

@app.post("/register-device")
async def register_device(body: RegisterRequest):
    device_tokens[body.user_id] = body.token
    print(f"Perangkat terdaftar: {body.user_id}")
    return {"status": "registered"}

@app.post("/trigger-notification")
async def trigger_notification(body: NotificationPayload):
    token = device_tokens.get(body.user_id)
    if not token:
        raise HTTPException(status_code=404, detail="User not found")
    
    await send_expo_notification(token, body.title, body.message)
    return {"status": "sent"}

# Endpoint baru untuk VS Code Task
@app.post("/send-custom-notification")
async def send_custom_notification(body: NotificationPayload):
    try:
        # Debugging: Cek isi token
        print(f"Mencoba mencari token untuk: {body.user_id}")
        token = device_tokens.get(body.user_id)
        
        if not token:
            print("Token tidak ditemukan!")
            raise HTTPException(status_code=404, detail="User not found")
        
        # Kirim notifikasi
        await send_expo_notification(token, body.title, body.message)
        print(f"Notifikasi sukses dikirim ke {body.user_id}")
        return {"status": "sent"}
    
    except Exception as e:
        print(f"Error terjadi: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)