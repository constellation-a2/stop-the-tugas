# Dokumentasi Algoritma Proyek

---

## 1. Algoritma Pengingat Tugas & Kuliah (Tim B)

1. **Mulai**
2. **Input**: Ruang kelas, dosen, waktu, dan materi.
3. **Proses**: Periksa waktu sekarang dan baca daftar jadwal dari database (meliputi ruang kelas, dosen, waktu, dan materi) melalui database jadwal kuliah dan tugas.
4. **Keputusan**: Apakah ada tugas dengan batas waktu `H-7`, `H-3`, atau `H-1`?
   * **Jika Ya** $\rightarrow$ **Output**: Siapkan data notifikasi tugas (materi tugas, tenggat waktu).
   * **Jika Tidak** $\rightarrow$ Lanjut ke langkah 5.
5. **Keputusan**: Apakah ada jadwal kuliah yang waktunya `H-1` atau `H-menit`?
   * **Jika Ya** $\rightarrow$ **Output**: Siapkan data notifikasi kuliah (mata kuliah/materi, dosen, ruang kelas, waktu).
   * **Jika Tidak** $\rightarrow$ Sistem akan melewati proses penyiapan notifikasi kuliah dan langsung menuju ke tahap *Proses Pengiriman Notifikasi*, atau selesai jika tidak ada notifikasi lain yang perlu dikirim.
   * **Keputusan (Proses Pengiriman Notifikasi)**: Apakah proses pengiriman notifikasi sedang berlangsung/berhasil?
     * **Jika Ya** $\rightarrow$ **Proses**: Sistem mencatat waktu keberhasilan pengiriman (`waktu_kirim`) ke dalam database *subscription*.
     * **Jika Tidak (Error)** $\rightarrow$ **Proses**: Sistem mencatat status `"Error"` ke dalam database *subscription*, kemudian melanjutkan pengiriman notifikasi lainnya tanpa menghentikan program.
6. **Proses**: Sistem melanjutkan pemeriksaan dan pengiriman notifikasi berikutnya hingga seluruh notifikasi yang perlu diproses selesai.
7. **Selesai**

---

## 2. Algoritma Kalender (Tim C)

1. **Mulai**
2. **Output**: Tampilkan Halaman Kalender Utama.
3. **Keputusan (Pilih Aksi)**:
   * **Opsi 1: Lihat Jadwal**
     1. Pilih tanggal di kalender.
     2. Sistem memfilter jadwal berdasarkan tipe (Tugas & Jadwal Kuliah).
     3. Tampilkan detail jadwal, lalu lanjut ke langkah 4 (**Selesai**).
   * **Opsi 2: Tambah Jadwal**
     1. **Pilih Tipe Jadwal**:
        * **Tugas**: Input data tugas (Nama, Deadline, Deskripsi).
        * **Jadwal Kuliah**: Input data kuliah (Matkul, Waktu, Ruang, Dosen, Deskripsi).
     2. **Keputusan**: Cek apakah data lengkap & valid?
        * **Tidak**: Tampilkan pesan error `"Data Belum Lengkap"`, lalu kembali ke *Pilih Tipe Jadwal*.
        * **Ya**:
          * Simpan data ke database.
          * Ambil data di database (daftar penerima notifikasi).
          * **Perulangan Pengiriman Notifikasi** (untuk setiap *subscriber*):
            1. **Cek**: Pengiriman sedang berlangsung?
               * **Ya**: Lewati proses pengiriman untuk mencegah pengiriman ganda, langsung lanjut ke langkah 3.
               * **Tidak**: Lanjut ke langkah 2.
            2. **Proses**: Kirim notifikasi & tandai sedang mengirim.
               * **Cek**: Pengiriman berhasil?
                 * **Ya**: Catat waktu berhasil di database *subscription*.
                 * **Tidak / Error**: Catat log error dan lanjut tanpa menghentikan proses (*lanjut tanpa stop*).
            3. **Cek**: Masih ada *subscriber* berikutnya?
               * **Ya**: Ulangi dari langkah 1 untuk *subscriber* berikutnya.
               * **Tidak**: Keluar dari perulangan.
          * Tampilkan jadwal baru di kalender, lalu lanjut ke langkah 4 (**Selesai**).
   * **Opsi 3: Hapus Jadwal**
     1. Pilih jadwal & klik hapus.
     2. **Keputusan**: Yakin hapus?
        * **Tidak**: Kembali ke langkah 2 (*Tampilkan Halaman Kalender Utama*).
        * **Ya**: Hapus data dari database, perbarui tampilan kalender, lalu lanjut ke langkah 4 (**Selesai**).
4. **Selesai**

---

## 3. Algoritma Upload Materi & Catatan (Tim D)

1. **Mulai**
2. **Output**: Tampilkan daftar file materi/catatan yang sudah diunggah.
3. **Keputusan (Pilih Aksi Pengguna)**:
   * **Jika Upload File (Create)**:
     * **Input**: Pilih label matkul, isi judul, nama pembuat, dan pilih file (PDF).
     * **Keputusan**: Apakah file berformat PDF dan ukuran $\le 10\text{ MB}$?
       * **Jika Ya** $\rightarrow$ **Proses**: Simpan file beserta waktu *upload* otomatis ke database.
       * **Jika Tidak** $\rightarrow$ **Output**: Tampilkan pesan error (kembali ke *Input*).
   * **Jika Baca/Unduh (Read)**:
     * **Input**: Klik judul file $\rightarrow$ **Output**: Buka/unduh file (PDF).
   * **Jika Hapus (Delete)**:
     * **Input**: Klik tombol hapus.
     * **Output**: Tampilkan fitur konfirmasi.
     * **Keputusan**: Konfirmasi hapus?
       * **Jika Ya** $\rightarrow$ **Proses**: Hapus file dari database.
       * **Jika Tidak** $\rightarrow$ Lanjut ke langkah 4.
4. **Selesai**