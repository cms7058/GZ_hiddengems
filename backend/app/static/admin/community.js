const $ = (selector) => document.querySelector(selector);
const state = { tab: 'eco', page: 1, total: 0, rows: [], editing: null };
const escape = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[char]));
const statuses = { pending: '待审核', approved: '通过', rejected: '不通过' };
async function api(path, method = 'GET', data) {
  const token = localStorage.getItem('gz_admin_token');
  if (!token) throw new Error('请先返回管理后台登录');
  const response = await fetch('/api/v1/admin/community' + path, { method, headers: { Authorization: 'Bearer ' + token, 'Content-Type': 'application/json' }, body: data ? JSON.stringify(data) : undefined });
  const body = await response.json();
  if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail || '请求失败'));
  return body;
}
const fail = (error) => { $('#message').textContent = error.message; };
async function load() {
  $('#message').textContent = '';
  const params = new URLSearchParams(new FormData($('#filters')));
  for (const [key, value] of [...params]) if (!value) params.delete(key);
  params.set('page', state.page);
  const data = await api(`/${state.tab}?${params}`);
  state.rows = data.items;
  state.total = data.total;
  $('#rows').innerHTML = data.items.map((row) => `<tr><td>${row.id}</td><td><button data-user="${row.user_id}">${escape(row.nickname)} #${row.user_id}</button></td><td>${escape(row.spot_name || row.title)}</td><td>${escape(row.category || row.reward_points + ' 积分')}</td><td>${statuses[row.status]}</td><td>${escape({ pending:'等待初审', completed:'已完成', manual_required:'需人工复核', not_required:'人工审核' }[row.ai_status] || '—')}</td><td>${escape(row.created_at)}</td><td><button data-review="${row.id}">${row.status === 'pending' ? '审核' : '查看'}</button></td></tr>`).join('') || '<tr><td colspan="8">暂无记录</td></tr>';
  $('#page').textContent = `${state.page} / ${Math.max(1, Math.ceil(data.total / 20))} · ${data.total} 条`;
  $('#previous').disabled = state.page === 1;
  $('#next').disabled = state.page * 20 >= data.total;
}
document.querySelectorAll('[data-tab]').forEach((button) => button.addEventListener('click', () => {
  state.tab = button.dataset.tab; state.page = 1;
  document.querySelectorAll('[data-tab]').forEach((item) => item.setAttribute('aria-pressed', String(item === button)));
  $('#reviews').hidden = false;
  load().catch(fail);
}));
$('#filters').addEventListener('submit', (event) => { event.preventDefault(); state.page = 1; load().catch(fail); });
$('#filters').addEventListener('reset', () => setTimeout(() => { state.page = 1; load().catch(fail); }, 0));
$('#previous').onclick = () => { state.page--; load().catch(fail); };
$('#next').onclick = () => { state.page++; load().catch(fail); };
$('#rows').onclick = async (event) => {
  try {
    const user = event.target.closest('[data-user]');
    if (user) {
      const summary = await api('/users/' + user.dataset.user);
      $('#userSummary').textContent = `环保信用：${summary.credit}\n环保打卡：${summary.checkin_count}\n警告：${summary.warning_count}\n` + Object.entries(summary.levels).map(([level,value]) => `L${level}: ${value}`).join(' · ') + '\n\n' + summary.warnings.map((row) => `${row.created_at} ${row.reason === 'unrelated' ? '内容完全无关' : '垃圾不清晰'}：清零信用 ${row.cleared_credits}、打卡次数 ${row.cleared_checkins}`).join('\n');
      $('#userDialog').showModal(); return;
    }
    const button = event.target.closest('[data-review]'); if (!button) return;
    const row = state.rows.find((item) => item.id === Number(button.dataset.review)); state.editing = row;
    $('#reviewTitle').textContent = `${row.spot_name || row.title} #${row.id}`;
    $('#details').textContent = `${row.nickname} #${row.user_id} · ${statuses[row.status]}\n${row.content || row.category + '类 / L' + row.level}\n${row.review_note}`;
    $('#media').replaceChildren();
    row.media.filter((item) => item.url).forEach((item) => {
      const url = new URL(item.url, location.origin);
      if (!['http:', 'https:'].includes(url.protocol)) return;
      const media = document.createElement(item.media_type === 'video' ? 'video' : 'img'); media.src = url.href; if (item.media_type === 'video') media.controls = true; else media.alt = row.title || '环保视频'; $('#media').append(media);
    });
    $('#aiResult').textContent = row.ai_note ? 'AI初审（仅供人工参考）：' + row.ai_note : '';
    $('#retryAI').hidden = state.tab !== 'eco' || row.category !== 'A' || row.status !== 'pending';
    $('#auditFields').hidden = row.status !== 'pending'; $('#reviewError').textContent = ''; $('#reviewForm').elements.note.value = '';
    $('#penaltyHint').hidden = state.tab !== 'eco';
    $('#verdict').innerHTML = state.tab === 'eco' ? '<option value="approved">通过</option><option value="unrelated">不通过：内容完全无关</option><option value="unclear_garbage">不通过：未呈现清晰可辨的入袋垃圾</option><option value="other">不通过：其他原因</option>' : '<option value="approved">通过并发放积分</option><option value="other">不通过</option>';
    $('#reviewDialog').showModal();
  } catch (error) { fail(error); }
};
$('#reviewForm').onsubmit = async (event) => {
  event.preventDefault();
  const verdict = $('#verdict').value;
  if (!window.confirm(verdict === 'approved' ? '确认通过审核？' : '确认不通过？环保违规可能触发警告及信用清零。')) return;
  $('#saveReview').disabled = true;
  try {
    const note = $('#reviewForm').elements.note.value;
    await api(`/${state.tab}/${state.editing.id}`, 'PATCH', state.tab === 'eco' ? { verdict, note } : { approved: verdict === 'approved', note });
    $('#reviewDialog').close(); await load(); await pending();
  } catch (error) { $('#reviewError').textContent = error.message; } finally { $('#saveReview').disabled = false; }
};
$('#retryAI').onclick = async () => {
  $('#retryAI').disabled = true;
  try { await api(`/eco/${state.editing.id}/ai`, 'POST'); $('#aiResult').textContent = '已提交AI初审，请稍后重新打开详情'; }
  catch (error) { $('#reviewError').textContent = error.message; } finally { $('#retryAI').disabled = false; }
};
document.querySelectorAll('[data-close]').forEach((button) => button.onclick = () => { const dialog = document.getElementById(button.dataset.close); dialog.querySelectorAll('video').forEach((v) => v.pause()); dialog.close(); });
async function pending() {
  if (document.hidden) return;
  try { const eco = await api('/eco?status=pending'); const food = await api('/food?status=pending'); $('#pending').textContent = `待审核：环保 ${eco.total} · 美食 ${food.total}`; } catch (error) { fail(error); }
}
load().catch(fail); pending(); setInterval(pending, 30000);
