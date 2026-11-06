<script setup lang="ts">
import { computed, onUnmounted, ref } from 'vue'
import { motion } from 'motion-v'
import { AudioLines, ArrowDownToLine, FolderOpen, Play, Square, Upload, CheckCircle2 } from 'lucide-vue-next'
import Button from './components/ui/button/Button.vue'
interface Job { status: string; message: string; percent: number; output?: string; duration?: number }
const text = ref('')
const reference = ref<File | null>(null)
const speed = ref(0.96)
const pause = ref(0.3)
const format = ref('mp3')
const consent = ref(false)
const error = ref('')
const job = ref<Job>({ status: 'idle', message: 'Sẵn sàng tạo giọng đọc', percent: 0 })
const pending = ref(false)
const connected = ref(true)
const busy = computed(() => pending.value || job.value.status === 'running')
const sessionToken = new URLSearchParams(location.search).get('token') || sessionStorage.getItem('voice-session') || ''
sessionStorage.setItem('voice-session', sessionToken)
history.replaceState({}, '', '/')
async function api(path: string, data?: object): Promise<Response> {
  const response = await fetch(path, { method: data ? 'POST' : 'GET', headers: { 'X-Session-Token': sessionToken, 'Content-Type': 'application/json' }, body: data ? JSON.stringify(data) : undefined })
  if (!response.ok) { const body: unknown = await response.json(); throw new Error(typeof body === 'object' && body !== null && 'error' in body && typeof body.error === 'string' ? body.error : 'Không thực hiện được yêu cầu.') }
  return response
}
async function chooseText(event: Event) {
  const element = event.target
  if (element instanceof HTMLInputElement) { const file = element.files?.item(0); if (file) text.value = await file.text() }
}
function chooseReference(event: Event) {
  const element = event.target
  if (element instanceof HTMLInputElement) reference.value = element.files?.item(0) || null
}
function encodeFile(file: File): Promise<string> {
  return new Promise((resolve, reject) => { const reader = new FileReader(); reader.onerror = () => reject(new Error('Không đọc được giọng mẫu.')); reader.onload = () => { if (typeof reader.result === 'string') resolve(reader.result.split(',')[1] || ''); else reject(new Error('File giọng mẫu không hợp lệ.')) }; reader.readAsDataURL(file) })
}
async function start() {
  error.value = ''; pending.value = true
  try {
    if (!text.value.trim()) throw new Error('Bạn hãy nhập nội dung cần đọc.')
    if (!consent.value) throw new Error('Hãy xác nhận quyền sử dụng giọng mẫu.')
    if (reference.value && reference.value.size > 30 * 1024 * 1024) throw new Error('Giọng mẫu tối đa 30 MB. Hãy chọn đoạn nói rõ khoảng 5–15 giây.')
    const audio = reference.value ? await encodeFile(reference.value) : null
    const response = await api('/api/start', { text: text.value, speed: speed.value, pause: pause.value, format: format.value, audio, audioName: reference.value?.name || '', consent: consent.value })
    job.value = await response.json()
  } catch (cause) { error.value = cause instanceof Error ? cause.message : 'Không tạo được âm thanh.' }
  finally { pending.value = false }
}
async function cancel() { try { job.value = await (await api('/api/cancel', {})).json() } catch (cause) { error.value = String(cause) } }
async function openFolder() { try { await api('/api/folder', {}) } catch (cause) { error.value = String(cause) } }
const timer = window.setInterval(async () => { try { job.value = await (await api('/api/status')).json(); connected.value = true } catch { connected.value = false } }, 1500)
onUnmounted(() => window.clearInterval(timer))
</script>
<template>
  <div class="shell">
    <header><div class="brand"><span class="brand-icon"><AudioLines :size="24" /></span><div>Giọng Việt <span>STUDIO</span></div></div><div class="local-badge"><i /> Xử lý trên máy của bạn</div></header>
    <motion.main :initial="{ opacity: 0, y: 12 }" :animate="{ opacity: 1, y: 0 }" :transition="{ duration: 0.35 }">
      <div class="intro"><div><p class="eyebrow">KHÔNG GIAN SÁNG TẠO ÂM THANH</p><h1>Câu chữ của bạn.<br /><span>Giọng nói đầy cảm xúc.</span></h1><p>Từ kịch bản đến lời đọc — chọn giọng, tinh chỉnh nhịp và tạo âm thanh.</p></div><div class="sound-art" aria-hidden="true"><div class="sound-orbit" /><div class="waveform"><i v-for="(height, index) in [16,26,42,29,58,77,45,92,63,38,71,50,29,62,43,22,36,18,12]" :key="index" :style="{ height: height + 'px' }" /></div><span>mỗi câu chữ, một sắc thái</span></div></div>
      <div class="workspace">
        <section class="card script-card" aria-labelledby="script-heading"><div class="section-top"><h2 id="script-heading"><span class="step">01</span> Nội dung lời đọc</h2><label class="text-import"><Upload :size="15" /> Chọn tệp TXT<input type="file" accept=".txt" @change="chooseText" :disabled="busy" /></label></div><label class="sr-only" for="script">Nội dung cần đọc</label><textarea id="script" v-model="text" :disabled="busy" placeholder="Dán kịch bản của bạn vào đây…&#10;&#10;Dùng dấu câu và xuống dòng để giọng đọc ngắt nghỉ tự nhiên." maxlength="30000" /><div class="script-footer"><span>Viết số thành chữ để đọc rõ hơn.</span><span>{{ text.length.toLocaleString('vi-VN') }} / 30.000 ký tự</span></div></section>
        <aside class="settings"><section class="card"><h2><span class="step">02</span> Giọng tham chiếu</h2><label class="upload-box"><AudioLines :size="28" /><strong>{{ reference ? reference.name : 'Giọng MC đã chuẩn bị' }}</strong><span>{{ reference ? 'Bấm để đổi file âm thanh' : 'Hoặc bấm để chọn giọng mẫu khác' }}</span><input type="file" accept=".wav,.mp3,.m4a,.flac,.ogg" @change="chooseReference" :disabled="busy" /></label><p class="hint">Mẫu khoảng 5–15 giây, một người nói rõ, ít nhạc và tạp âm.</p><label class="consent"><input type="checkbox" v-model="consent" :disabled="busy" /><span>Tôi là người nói hoặc đã được đồng ý cho tạo và sử dụng giọng này.</span></label></section>
        <section class="card"><h2><span class="step">03</span> Nhịp đọc & định dạng</h2><label class="slider-label" for="speed">Tốc độ <strong>{{ Number(speed).toFixed(2) }}×</strong></label><input id="speed" type="range" min="0.75" max="1.25" step="0.01" v-model.number="speed" :disabled="busy" /><label class="slider-label" for="pause">Nghỉ giữa đoạn <strong>{{ Number(pause).toFixed(2) }} giây</strong></label><input id="pause" type="range" min="0" max="1.5" step="0.05" v-model.number="pause" :disabled="busy" /><label class="select-label" for="format">File xuất</label><select id="format" v-model="format" :disabled="busy"><option value="mp3">MP3 · dễ chia sẻ</option><option value="wav">WAV · âm thanh không nén</option></select></section></aside>
      </div>
      <section class="render-bar card"><span class="render-icon"><AudioLines :size="24" /></span><div class="render-info" role="status" aria-live="polite"><strong>{{ connected ? job.message : 'Mất kết nối ứng dụng. Hãy mở lại file EXE.' }}</strong><span>{{ busy ? 'Bạn có thể theo dõi tiến độ ngay tại đây.' : 'Âm thanh được tạo và lưu riêng trên máy của bạn.' }}</span><progress v-if="busy" max="100" :value="job.percent" aria-label="Tiến độ tạo giọng" /></div><Button v-if="busy" variant="outline" @click="cancel"><Square :size="16" /> Dừng</Button><Button v-else @click="start" :disabled="!connected"><Play :size="17" /> Tạo âm thanh</Button></section>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <motion.section v-if="job.status === 'completed' && job.output" class="card result" :initial="{ opacity: 0 }" :animate="{ opacity: 1 }"><div><h2><CheckCircle2 :size="20" /> Âm thanh của bạn đã sẵn sàng</h2><p>{{ job.output }} · {{ Math.round(job.duration || 0) }} giây</p></div><audio controls :src="'/audio/' + encodeURIComponent(job.output)" /><div class="result-actions"><a class="button button-primary" :href="'/audio/' + encodeURIComponent(job.output) + '?download=1'" download><ArrowDownToLine :size="16" /> Lưu file</a><Button variant="outline" @click="openFolder"><FolderOpen :size="16" /> Thư mục</Button></div></motion.section>
      <footer>Giọng Việt Studio · Bản portable Windows x64 <span>Để tắt hoàn toàn, đóng cửa sổ ứng dụng trên thanh tác vụ.</span></footer>
    </motion.main>
  </div>
</template>
