# Simple Chatbot với Pipecat và LiveKit

Một chatbot đơn giản sử dụng Pipecat framework với LiveKit WebRTC transport cho giao tiếp voice real-time.

## Kiến trúc

**Option A (Khuyến nghị cho Production): WebRTC + LiveKit + Pipecat LiveKitTransport**

```
Client (web/mobile) ↔ LiveKit (WebRTC SFU/media server) ↔ Pipecat agent (container)
```

Pipecat agent "join" vào room như một participant, nhận audio stream realtime, chạy pipeline (VAD/STT/LLM/TTS) và trả audio lại realtime.

## Tính năng

- ✅ Real-time voice conversation qua WebRTC
- ✅ Speech-to-Text (STT) sử dụng Deepgram
- ✅ Language Model (LLM) sử dụng OpenAI GPT-4o-mini
- ✅ Text-to-Speech (TTS) sử dụng OpenAI TTS
- ✅ Voice Activity Detection (VAD) với Silero
- ✅ Hỗ trợ interruption (người dùng có thể ngắt bot)
- ✅ Container hóa với Docker
- ✅ Dễ dàng scale với LiveKit Agents model

## Yêu cầu

- Python 3.11+
- Docker và Docker Compose (cho container deployment)
- LiveKit server (self-hosted hoặc LiveKit Cloud)
- OpenAI API key
- Deepgram API key (cho STT)

## Setup

### 1. Cấu hình biến môi trường

Tạo file `.env` từ template:

```bash
cp env.example .env
```

Cập nhật các giá trị trong `.env`:

```ini
# LiveKit Configuration (Required)
LIVEKIT_URL=wss://your-livekit-server.livekit.cloud
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret

# Optional: Room và participant configuration
LIVEKIT_ROOM=default-room
LIVEKIT_PARTICIPANT_NAME=assistant

# OpenAI Configuration (Required)
OPENAI_API_KEY=your_openai_api_key

# Deepgram Configuration (Required for STT)
DEEPGRAM_API_KEY=your_deepgram_api_key
```

### 2. Triển khai LiveKit Server

Bạn có 2 lựa chọn:

#### Option 1: LiveKit Cloud (Khuyến nghị cho bắt đầu)

1. Đăng ký tại [LiveKit Cloud](https://cloud.livekit.io)
2. Tạo project và lấy:
   - `LIVEKIT_URL` (ví dụ: `wss://your-project.livekit.cloud`)
   - `LIVEKIT_API_KEY`
   - `LIVEKIT_API_SECRET`

#### Option 2: Self-hosted LiveKit

**Với Docker:**

```bash
docker run -d \
  --name livekit-server \
  -p 7880:7880 \
  -p 50000-50100:50000-50100/udp \
  -e LIVEKIT_KEYS=your_api_key:your_api_secret \
  livekit/livekit-server:latest --dev
```

**Với Kubernetes:**

LiveKit yêu cầu cấu hình đặc biệt cho WebRTC:

- Sử dụng `hostNetwork: true`
- Map đúng các ports UDP cho RTC (50000-50100)
- Mỗi node chỉ nên chạy một pod LiveKit
- Không phù hợp với serverless/private cluster do NAT nhiều lớp

Xem thêm: [LiveKit Kubernetes Docs](https://docs.livekit.io/home/self-hosting/kubernetes/)

### 3. Chạy Bot

#### Cách 1: Chạy trực tiếp với Python

```bash
# Cài đặt dependencies
pip install "pipecat-ai[livekit]" python-dotenv livekit

# Chạy bot
python main.py
```

#### Cách 2: Chạy với Docker

```bash
# Build image
docker build -t simple-bot .

# Chạy container
docker run --env-file .env simple-bot
```

#### Cách 3: Chạy với Docker Compose

```bash
# Chạy bot
docker-compose up -d

# Xem logs
docker-compose logs -f pipecat-agent
```

## Cách hoạt động

1. **Bot kết nối**: Bot join vào LiveKit room như một participant
2. **User kết nối**: User (web/mobile client) join vào cùng room
3. **Audio Input**: Bot nhận audio stream từ user qua LiveKit
4. **Pipeline xử lý**:
   - **VAD**: Phát hiện khi user nói
   - **STT**: Chuyển speech thành text (Deepgram)
   - **LLM**: Xử lý và tạo response (OpenAI GPT-4o-mini)
   - **TTS**: Chuyển text thành speech (OpenAI TTS)
5. **Audio Output**: Bot gửi audio stream lại cho user qua LiveKit

## Client Side

Để kết nối từ web client, bạn cần:

1. Sử dụng `pipecat-client-web` hoặc LiveKit SDK
2. Generate token để join room (từ LiveKit server)
3. Kết nối đến cùng `LIVEKIT_URL` và `LIVEKIT_ROOM`

Ví dụ với LiveKit JavaScript SDK:

```javascript
import { Room, RoomEvent } from "livekit-client";

const room = new Room();
await room.connect("wss://your-livekit-server.livekit.cloud", token);

// Enable microphone
await room.localParticipant.setMicrophoneEnabled(true);

// Listen for audio tracks
room.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
  if (track.kind === "audio") {
    const audioElement = track.attach();
    document.body.appendChild(audioElement);
  }
});
```

## Scale và Production

### LiveKit Agents Model

Với mô hình LiveKit Agents:

- Triển khai theo worker pool
- LiveKit tự động phân phối job qua các agent servers
- Mỗi job spawn subprocess cho phiên làm việc
- Phù hợp với voice session (stateful theo phiên)
- Tránh bài toán "sticky session" phức tạp ở L7

### Khi nào chọn Option A (WebRTC + LiveKit)

- ✅ Người dùng ở mạng đa dạng (mobile/4G, NAT)
- ✅ Cần chống packet loss/jitter tốt
- ✅ Muốn latency ổn định, trải nghiệm "đàm thoại" mượt
- ✅ Muốn scale đa phiên có kỷ luật

## Cấu trúc Project

```
simple-bot/
├── main.py              # Bot chính với Pipecat pipeline
├── pyproject.toml       # Python dependencies
├── Dockerfile           # Container image
├── docker-compose.yml   # Docker Compose configuration
├── env.example          # Template cho biến môi trường
└── README.md           # Tài liệu này
```

## Troubleshooting

### Bot không kết nối được đến LiveKit

- Kiểm tra `LIVEKIT_URL` có đúng format `wss://...` không
- Kiểm tra `LIVEKIT_API_KEY` và `LIVEKIT_API_SECRET` có đúng không
- Đảm bảo LiveKit server đang chạy và accessible từ container

### Audio không hoạt động

- Kiểm tra VAD settings trong code
- Đảm bảo user đã enable microphone
- Kiểm tra network connectivity và firewall rules cho UDP ports

### Lỗi OpenAI API

- Kiểm tra `OPENAI_API_KEY` có hợp lệ không
- Kiểm tra quota và billing của OpenAI account

### Lỗi Deepgram API

- Kiểm tra `DEEPGRAM_API_KEY` có hợp lệ không
- Đảm bảo bạn đã đăng ký và có credits trong Deepgram account

### Lỗi khi chạy trong Docker

- Đảm bảo `.env` file được mount đúng
- Kiểm tra logs: `docker-compose logs pipecat-agent`
- Kiểm tra network connectivity từ container đến LiveKit server

## Tài liệu tham khảo

- [Pipecat Documentation](https://docs.pipecat.ai)
- [LiveKit Documentation](https://docs.livekit.io)
- [LiveKit Self-hosting Guide](https://docs.livekit.io/home/self-hosting/)
- [Pipecat LiveKit Transport](https://docs.pipecat.ai/server/services/transport/livekit)

## License

MIT
