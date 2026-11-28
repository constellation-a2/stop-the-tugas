# Stop The Tugas REST API

Dokumen ini menjadi kontrak frontend sementara untuk entrypoint Flask di
`api/index.py`. Repository belum berisi `database/physical/schema.sql` dan
`seed.sql`; nama field payload pada dokumen ini diturunkan dari README dan harus
dicocokkan dengan kedua file tersebut saat tersedia.


## Konvensi

- Base path: `/api/v1`.
- Request dan response menggunakan JSON, kecuali upload Materi yang memakai
  `multipart/form-data`.
- Response sukses menggunakan envelope `{"data": ...}`. Error menggunakan
  `{"error": {"code": "...", "message": "..."}}`.
- Semua waktu agenda harus berupa ISO-8601 dengan offset zona waktu. Kalender
  menggunakan `Asia/Jakarta` (WIB); timestamp disimpan sebagai `TIMESTAMPTZ`
  oleh service/database adapter.
- Tipe `string`, `integer`, `boolean`, `object`, `array`, `null`, dan `binary`
  di bawah mengacu pada tipe JSON atau multipart. `string | null` berarti field
  boleh berisi string atau `null`; field opsional boleh tidak dikirim.
- Tidak ada login atau user account dalam MVP.
- Field tambahan pada response (misalnya `id`, `download_url`) mengikuti
  implementasi adapter database/storage setelah schema disediakan.

### Integrasi backend

`create_app(services=...)` menerima adapter yang mengimplementasikan operasi
database, Web Push, dan persistent object storage. Saat adapter belum dipasang,
endpoint yang membutuhkan data mengembalikan `503 service_unavailable`;
entrypoint ini tidak menggunakan penyimpanan in-memory atau disk lokal.
Implementasi adapter menunggu schema/seed agar tidak menebak struktur database.

## 1. Reminder

Jadwal pengingat yang harus dijalankan oleh service:

- `TUGAS`: H-7, H-3, dan H-1; interval yang sudah lewat tidak dijadwalkan.
- `KULIAH`: H-1 pukul 19:00 WIB dan H-30 menit sebelum kelas.
- Dispatch harus mencegah pengiriman ganda menggunakan `claimed_at` dan
  `FOR UPDATE SKIP LOCKED` di PostgreSQL.
- Perubahan/penghapusan agenda harus memperbarui atau membatalkan pengingat
  terkait di service.

### Mendapatkan VAPID public key

`GET /api/v1/reminders/vapid-public-key`

Request: tidak ada.

Response `200`:

```json
{
  "data": {
    "public_key": "BASE64URL_VAPID_PUBLIC_KEY"
  }
}
```

| Key | Tipe | Keterangan |
| --- | --- | --- |
| `data` | object | Envelope response |
| `data.public_key` | string | VAPID public key |

Jika `VAPID_PUBLIC_KEY` belum dikonfigurasi, response `503 service_unavailable`.

### Menyimpan/memperbarui Web Push subscription

`PUT /api/v1/reminders/subscriptions`

Request:

```json
{
  "endpoint": "https://push.example/subscription",
  "expirationTime": null,
  "keys": {
    "p256dh": "CLIENT_PUBLIC_KEY",
    "auth": "CLIENT_AUTH_SECRET"
  }
}
```

| Key | Tipe | Wajib | Keterangan |
| --- | --- | --- | --- |
| `endpoint` | string | Ya | URL push service |
| `expirationTime` | integer \| null | Tidak | Unix timestamp dalam milidetik, atau `null` |
| `keys` | object | Ya | Kunci Web Push |
| `keys.p256dh` | string | Ya | Public key client |
| `keys.auth` | string | Ya | Auth secret client |

Response `200`:

```json
{
  "data": {
    "endpoint": "https://push.example/subscription"
  }
}
```

| Key | Tipe | Keterangan |
| --- | --- | --- |
| `data` | object | Envelope response |
| `data.endpoint` | string | URL subscription yang tersimpan |

### Menghapus Web Push subscription

`DELETE /api/v1/reminders/subscriptions`

Request:

```json
{
  "endpoint": "https://push.example/subscription"
}
```

| Key | Tipe | Wajib | Keterangan |
| --- | --- | --- | --- |
| `endpoint` | string | Ya | URL subscription yang akan dihapus |

Response `200`: `{"data": {"deleted": true}}`.

| Key | Tipe |
| --- | --- |
| `data` | object |
| `data.deleted` | boolean |

### Menjalankan dispatch pengingat (cron)

`POST /api/v1/reminders/dispatch`

Header: `Authorization: Bearer <CRON_SECRET>`.
Tipe header: string.

Request: tidak ada.

Response `200` (bentuk data dispatch ditentukan adapter):

```json
{
  "data": {
    "sent": 12,
    "failed": 0
  }
}
```

| Key | Tipe | Keterangan |
| --- | --- | --- |
| `data` | object | Ringkasan dispatch dari adapter |
| `data.sent` | integer | Jumlah pengingat terkirim |
| `data.failed` | integer | Jumlah pengiriman gagal |

## 2. Calendar

Agenda menggunakan `agenda_type` bernilai `TUGAS` atau `KULIAH`, `title`, dan
`course_label`. Waktu harus mencakup timezone offset, misalnya `+07:00`.
`TUGAS` memerlukan `due_at`; `KULIAH` memerlukan `starts_at` dan `class_loc`,
dengan `ends_at` opsional. `description` opsional.

Tipe objek agenda pada response:

| Key | Tipe | Wajib | Keterangan |
| --- | --- | --- | --- |
| `id` | string | Ya | ID agenda |
| `agenda_type` | string (`TUGAS` \| `KULIAH`) | Ya | Jenis agenda |
| `title` | string | Ya | Judul |
| `course_label` | string | Ya | Label mata kuliah |
| `due_at` | string (ISO-8601) | Untuk `TUGAS` | Tenggat dengan offset zona waktu |
| `starts_at` | string (ISO-8601) | Untuk `KULIAH` | Waktu mulai dengan offset zona waktu |
| `ends_at` | string (ISO-8601) \| null | Tidak | Waktu selesai kelas |
| `class_loc` | string | Untuk `KULIAH` | Lokasi kelas |
| `description` | string \| null | Tidak | Catatan agenda |

### Ringkasan agenda bulanan

`GET /api/v1/calendar/month?year=2026&month=11`

Request: query `year` dan `month` dikirim sebagai string pada URL, lalu diparse
menjadi integer (`year`: 1-9999, `month`: 1-12).

Response `200`; tanggal tanpa agenda tetap ditampilkan frontend sebagai tanggal
kosong, dan service dapat mengembalikan daftar kosong:

```json
{
  "data": [],
  "timezone": "Asia/Jakarta"
}
```

| Key | Tipe | Keterangan |
| --- | --- | --- |
| `data` | array of Agenda | Daftar agenda untuk bulan tersebut; dapat kosong |
| `timezone` | string | Selalu `Asia/Jakarta` |

### Agenda harian

`GET /api/v1/calendar/day?date=2026-11-30`

Request: query `date` bertipe string dengan format `YYYY-MM-DD`.

Response `200`:

```json
{
  "data": [],
  "timezone": "Asia/Jakarta"
}
```

| Key | Tipe | Keterangan |
| --- | --- | --- |
| `data` | array of Agenda | Daftar agenda hari tersebut; dapat kosong |
| `timezone` | string | Selalu `Asia/Jakarta` |

Daftar kosong berarti tidak ada tugas atau jadwal kuliah pada tanggal tersebut.

### Membuat agenda tugas

`POST /api/v1/agendas`

Request:

```json
{
  "agenda_type": "TUGAS",
  "title": "Essay",
  "course_label": "BIO101",
  "due_at": "2026-11-30T23:59:00+07:00",
  "description": "Bab 4-5"
}
```

| Key | Tipe | Wajib | Keterangan |
| --- | --- | --- | --- |
| `agenda_type` | string (`TUGAS`) | Ya | Jenis agenda |
| `title` | string | Ya | Judul tugas |
| `course_label` | string | Ya | Label mata kuliah |
| `due_at` | string (ISO-8601) | Ya | Tenggat dengan offset zona waktu |
| `description` | string | Tidak | Catatan tugas |

Response `201`:

```json
{
  "data": {
    "id": "AGENDA_ID",
    "agenda_type": "TUGAS",
    "title": "Essay",
    "course_label": "BIO101",
    "due_at": "2026-11-30T23:59:00+07:00",
    "description": "Bab 4-5"
  }
}
```

`data` bertipe Agenda.

### Membuat jadwal kuliah

`POST /api/v1/agendas`

Request:

```json
{
  "agenda_type": "KULIAH",
  "title": "Biology",
  "course_label": "BIO101",
  "starts_at": "2026-11-30T09:00:00+07:00",
  "ends_at": "2026-11-30T10:30:00+07:00",
  "class_loc": "Room 2"
}
```

| Key | Tipe | Wajib | Keterangan |
| --- | --- | --- | --- |
| `agenda_type` | string (`KULIAH`) | Ya | Jenis agenda |
| `title` | string | Ya | Nama mata kuliah/jadwal |
| `course_label` | string | Ya | Label mata kuliah |
| `starts_at` | string (ISO-8601) | Ya | Waktu mulai dengan offset zona waktu |
| `ends_at` | string (ISO-8601) | Tidak | Waktu selesai dengan offset zona waktu |
| `class_loc` | string | Ya | Lokasi kelas |
| `description` | string | Tidak | Catatan jadwal |

Response `201`: bentuk `data` mengikuti record agenda yang dibuat.
`data` bertipe Agenda.

### Menghapus agenda

`DELETE /api/v1/agendas/{agenda_id}`

Request: tidak ada. Frontend harus meminta konfirmasi sebelum memanggil endpoint.
Path parameter `agenda_id`: string.

Response `200`: `{"data": {"deleted": true}}`. Service harus membatalkan
pengingat yang masih pending untuk agenda tersebut.

| Key | Tipe |
| --- | --- |
| `data` | object |
| `data.deleted` | boolean |

## 3. Materi CRD

Materi hanya menyediakan Create, Read, dan Delete; tidak ada endpoint Update.
File hanya PDF, wajib ber-ekstensi `.pdf`, `Content-Type: application/pdf`,
memiliki header `%PDF-`, dan berukuran maksimal 10 MiB (`10485760` byte).
Adapter storage wajib memakai persistent object storage pada deployment
serverless, bukan folder lokal.

### Daftar materi

`GET /api/v1/materials?course_label=BIO101`

Query `course_label` opsional.
Tipe query `course_label`: string.

Response `200`:

```json
{
  "data": [
    {
      "id": "MATERIAL_ID",
      "course_label": "BIO101",
      "title": "Lecture 1",
      "creator": "Ari",
      "download_url": "https://storage.example/material.pdf"
    }
  ]
}
```

| Key | Tipe | Keterangan |
| --- | --- | --- |
| `data` | array of Material | Daftar materi; dapat kosong |
| `data[].id` | string | ID materi |
| `data[].course_label` | string | Label mata kuliah |
| `data[].title` | string | Judul materi |
| `data[].creator` | string | Nama pembuat |
| `data[].download_url` | string | URL akses/unduh dari object storage |

### Upload materi

`POST /api/v1/materials`

Request `multipart/form-data`:

| Field | Tipe | Wajib | Keterangan |
| --- | --- | --- | --- |
| `course_label` | string (text) | Ya | Label mata kuliah |
| `title` | string (text) | Ya | Judul materi |
| `creator` | string (text) | Ya | Nama pembuat, dapat diisi dari `localStorage` frontend |
| `file` | binary (file) | Ya | PDF `application/pdf`, maksimal 10 MiB |

Response `201`:

```json
{
  "data": {
    "id": "MATERIAL_ID",
    "course_label": "BIO101",
    "title": "Lecture 1",
    "creator": "Ari",
    "download_url": "https://storage.example/material.pdf"
  }
}
```

| Key | Tipe | Keterangan |
| --- | --- | --- |
| `data` | Material | Record materi yang tersimpan |
| `data.id` | string | ID materi |
| `data.course_label` | string | Label mata kuliah |
| `data.title` | string | Judul materi |
| `data.creator` | string | Nama pembuat |
| `data.download_url` | string | URL akses/unduh dari object storage |

### Membaca metadata materi

`GET /api/v1/materials/{material_id}`

Request: tidak ada.
Path parameter `material_id`: string.

Response `200`: `data` berisi metadata materi dan URL akses file.
`data` bertipe Material dengan field yang sama seperti response daftar materi.

### Menghapus materi

`DELETE /api/v1/materials/{material_id}`

Request: tidak ada. Frontend harus meminta konfirmasi sebelum menghapus.
Path parameter `material_id`: string.

Response `200`: `{"data": {"deleted": true}}`.

| Key | Tipe |
| --- | --- |
| `data` | object |
| `data.deleted` | boolean |

## Kode error

Semua error menggunakan bentuk:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Penjelasan singkat untuk frontend"
  }
}
```

| Key | Tipe | Keterangan |
| --- | --- | --- |
| `error` | object | Detail error |
| `error.code` | string | Kode error stabil |
| `error.message` | string | Pesan yang dapat ditampilkan frontend |

| HTTP | `code` | Arti |
| --- | --- | --- |
| `400` | `invalid_json` / `validation_error` / `bad_request` | JSON, field, tanggal, atau parameter tidak valid |
| `401` | `unauthorized` | Token cron tidak ada atau tidak valid |
| `404` | `not_found` | Agenda atau materi tidak ditemukan |
| `405` | `method_not_allowed` | Method HTTP tidak didukung |
| `413` | `file_too_large` | Ukuran file melebihi 10 MiB |
| `415` | `unsupported_media_type` / `invalid_pdf` | Ekstensi, MIME type, atau header bukan PDF |
| `500` | `http_error` | Kesalahan HTTP server yang tidak dirinci |
| `503` | `service_unavailable` | Integrasi backend, Web Push, atau konfigurasi layanan belum tersedia |