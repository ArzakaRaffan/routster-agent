# Routster Agent

Coding agent di terminal yang ditenagai **[Routster](https://routster.trackster.dev)**: satu API
key, banyak model (DeepSeek, GLM, Kimi, MiniMax, dan lain-lain), saldo dalam Rupiah.

Ketik tugas, lalu agent membaca file, mengedit, menjalankan perintah shell (dengan konfirmasi), dan
mengulang sampai tugasnya selesai.

> Routster Agent adalah fork dari **[Hermes Agent](https://github.com/NousResearch/hermes-agent)
> buatan Nous Research** (lisensi MIT). Seluruh TUI, agent loop, tools, dan sandbox berasal dari
> Hermes. README asli Hermes ada di [README.hermes.md](README.hermes.md), dan perubahan fork ini
> dicatat di [FORK.md](FORK.md).

## Mulai dalam 2 menit

1. **Ambil API key.** Daftar di <https://routster.trackster.dev>, top up saldo (QRIS), lalu salin
   API key dari [dashboard](https://routster.trackster.dev/dashboard).
2. **Instal dari source** (butuh `git` dan [`uv`](https://docs.astral.sh/uv/); repo-nya besar, sekitar 300 MB):

   ```bash
   git clone https://github.com/ArzakaRaffan/routster-agent.git
   cd routster-agent
   uv python install 3.14
   "$(uv python find 3.14)" -m pm.build_env --source . --out ~/.local/share/routster-agent/venv
   mkdir -p ~/.local/bin && ln -sf ~/.local/share/routster-agent/venv/bin/routster ~/.local/bin/routster
   ```

   Pastikan `~/.local/bin` ada di `PATH`. `pip install`/`uv tool install` biasa **tidak** bisa
   dipakai, karena pin dependensi upstream hanya bisa di-resolve lewat `uv.lock` + PM.

3. **Login dan mulai:**

   ```bash
   routster login     # tempel API key (input disembunyikan), divalidasi tanpa memotong saldo
   routster           # mulai sesi di folder project kamu
   ```

Paket instal satu baris (`pipx`/`uv tool install`) belum tersedia. Lihat bagian *Status* di bawah.

## Perintah penting

| Perintah | Fungsi |
|---|---|
| `routster` | Sesi interaktif (TUI) |
| `routster -z "tugas"` | Satu tugas sekali jalan, tanpa interaksi |
| `routster login` | Simpan dan validasi API key Routster, jadikan Routster provider default |
| `routster model` | Pilih model. Multiplier input/output tiap model ditampilkan |
| `routster setup` | Wizard setup lengkap (Quick Setup = Routster) |
| `routster doctor` | Cek konfigurasi |

## Model dan biaya

Saldo dipotong `input_tokens × input_multiplier + output_tokens × output_multiplier` per request,
dan satu tugas agent bisa memanggil API berkali-kali. Daftar model selalu diambil dari
`/v1/models`, dan picker `routster model` menampilkan multiplier-nya.

- Default: `routster/deepseek-v4.1-flash` (multiplier 1×/1×, murah).
- Direkomendasikan untuk agent (dikurasi manual): `routster/deepseek-v4-pro`, `routster/glm-5.3`,
  `routster/glm-5.3-flash`, `routster/kimi-k2.7`, `routster/minimax-m3`.
- Agent selalu mengirim `max_tokens` (default 8192). Gateway memesan saldo sebesar `max_tokens`
  sebelum request jalan, jadi naikkan lewat `model.max_tokens` di config hanya kalau perlu.

## Keamanan

- API key disimpan di `~/.hermes/.env` dengan permission `600`, atau dibaca dari env `ROUTSTER_API_KEY`.
  Jangan commit key ke repo.
- Perintah shell yang berbahaya meminta persetujuan dulu (mode approval `smart` bawaan Hermes).
  `--yolo` mematikan konfirmasi, jadi gunakan dengan hati-hati.
- Sandbox: secara default perintah dijalankan langsung di mesin kamu. Untuk isolasi, pilih backend
  Docker, SSH, Modal, Daytona, atau Vercel Sandbox lewat `routster setup terminal`.
- Routster tidak menyimpan isi prompt/response, hanya metadata (jumlah token, model, status).

## Konfigurasi lanjutan

| Variabel / key | Fungsi |
|---|---|
| `ROUTSTER_API_KEY` | API key (alternatif dari `routster login`) |
| `ROUTSTER_BASE_URL` | Ganti gateway, misalnya staging atau `http://localhost:8000/v1` |
| `model.max_tokens` (config.yaml) | Batas output per request (maks. 32768) |

Provider lain (OpenRouter, Anthropic, dan lain-lain) tetap bisa dipakai lewat `routster model` atau
config. Routster cuma jadi default.

## Status

Ini versi awal. Yang belum dikerjakan:

- Teks dan banner di TUI sebagian masih bertuliskan "Hermes".
- `routster update` masih menarik update dari repo Hermes upstream, jadi **jangan dipakai dulu**.
  Untuk update: `git pull`, hapus folder venv, lalu jalankan lagi perintah `pm.build_env` di atas.
- Installer satu baris (`curl … | bash`) belum ada.
- Saldo belum tampil di status bar, karena gateway belum punya endpoint saldo berbasis API key.

## Lisensi

MIT, sama seperti Hermes Agent. Copyright (c) 2025 Nous Research untuk kode Hermes. Lihat
[LICENSE](LICENSE).
