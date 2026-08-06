from pyngrok import ngrok
import time

tunnel = ngrok.connect(8000, "http")
print("NGROK_URL=", tunnel.public_url)
with open("ngrok_url.txt", "w") as f:
    f.write(tunnel.public_url)

# Keep process alive so the tunnel stays up
try:
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    ngrok.disconnect(tunnel.public_url)
    print("ngrok stopped")
