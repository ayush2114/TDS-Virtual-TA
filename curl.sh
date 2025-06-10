curl "https://afd6-42-105-48-85.ngrok-free.app/ask" \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"I know Docker but have not used Podman before. Should I use Docker for this course?\", \"image\": \"$(base64 -w0 project-tds-virtual-ta-q1.webp)\"}"