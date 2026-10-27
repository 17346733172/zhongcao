import assert from 'node:assert/strict';
import { spawn, spawnSync, execFileSync } from 'node:child_process';
import { createWriteStream } from 'node:fs';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { randomBytes, randomUUID } from 'node:crypto';
import net from 'node:net';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const qaRoot = path.join(root, 'backend/.qa');
const runDir = path.join(qaRoot, randomUUID());
await mkdir(runDir, { recursive: true });
const { chromium } = await import(pathToFileURL(path.join(qaRoot, 'browser/node_modules/playwright/index.mjs')).href);
const python = path.join(root, 'backend/.venv/Scripts/python.exe');
const origin = 'http://127.0.0.1:3000';
const password = randomBytes(20).toString('base64url');
const replacement = randomBytes(20).toString('base64url');
const env = { ...process.env, DATABASE_PATH: path.join(runDir, 'test.db'), ALLOWED_ORIGINS: origin, COOKIE_SECURE: 'false' };
const processes = [];
let browser;
const errors = [];
async function portFree(port) {
  await new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once('error', () => reject(new Error(`验收端口 ${port} 已占用；请先停止已有前后端。`)));
    server.listen(port, '127.0.0.1', () => server.close(resolve));
  });
}
async function ready(url) {
  for (let attempt = 0; attempt < 80; attempt++) {
    try { if ((await fetch(url, { signal: AbortSignal.timeout(1000) })).ok) return; } catch {}
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  throw new Error(`服务未启动：${url}`);
}
function start(command, args, cwd, name, environment = env) {
  const log = createWriteStream(path.join(runDir, `${name}.log`));
  const child = spawn(command, args, { cwd, env: environment, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
  child.stdout.pipe(log); child.stderr.pipe(log);
  processes.push(child);
}
async function noOverflow(page, label) {
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `${label} 横向溢出`);
}
async function login(page, username, secret = password) {
  await page.goto(`${origin}/login`);
  await page.getByLabel('账号', { exact: true }).fill(username);
  await page.getByLabel('密码', { exact: true }).fill(secret);
  await page.getByRole('button', { name: '登录', exact: true }).click();
  await page.waitForURL(origin + '/');
  await page.getByRole('heading', { name: '中药基础资料', exact: true }).waitFor();
  await page.getByRole('button', { name: '刷新共享资料', includeHidden: true }).waitFor({ state: 'attached' });
  await page.waitForFunction(() => !document.querySelector('.document-feedback'));
}
function observe(page) { page.on('pageerror', error => errors.push(error.message)); }
function pass(name) { console.log(`PASS ${name}`); }

try {
  await portFree(3000); await portFree(8000);
  const init = spawnSync(python, ['-c', `import json,sys,time; from app.config import Settings; from app.database import Database; from app.security import hash_password; p=json.load(sys.stdin); d=Database(Settings.from_env().database); d.initialize(); c=d.connect(); db=c.__enter__(); db.execute('INSERT INTO users(username,display_name,password_hash,role,created_at) VALUES(?,?,?,?,?)', ('qa_admin','验收管理员',hash_password(p['password']),'admin',int(time.time()))); c.__exit__(None,None,None)`], { cwd: path.join(root, 'backend'), env, input: JSON.stringify({ password }), encoding: 'utf8', windowsHide: true });
  assert.equal(init.status, 0, '无法初始化隔离验收数据库');
  start(python, ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000', '--no-proxy-headers', '--no-access-log'], path.join(root, 'backend'), 'backend');
  start(process.execPath, ['node_modules/next/dist/bin/next', 'start', '--hostname', '127.0.0.1', '--port', '3000'], path.join(root, 'frontend'), 'frontend');
  await ready('http://127.0.0.1:8000/api/health'); await ready(origin + '/login');
  browser = await chromium.launch({ executablePath: process.env.BROWSER_EXECUTABLE ?? 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless: true });
  const adminContext = await browser.newContext({ viewport: { width: 1487, height: 1058 } });
  const admin = await adminContext.newPage(); observe(admin);
  await admin.goto(origin + '/admin'); await admin.waitForURL('**/login');
  await admin.screenshot({ path: path.join(root, 'design/login-desktop.png'), fullPage: true });
  await noOverflow(admin, '桌面登录');
  await admin.getByLabel('账号', { exact: true }).fill('qa_admin');
  await admin.getByLabel('密码', { exact: true }).fill('wrong-password');
  await admin.getByRole('button', { name: '登录', exact: true }).click();
  await admin.getByRole('alert').filter({ hasText: '账号或密码错误' }).waitFor();
  await login(admin, 'qa_admin');
  pass('未登录跳转、错误密码与管理员真实登录');
  await admin.getByRole('link', { name: '账号管理', exact: true }).click();
  await admin.getByRole('heading', { name: '账号与权限管理' }).waitFor();
  for (const [username, name, role] of [['qa_editor', '验收编辑员', 'editor'], ['qa_viewer', '验收普通用户', 'viewer']]) {
    await admin.getByLabel('登录账号', { exact: true }).fill(username);
    await admin.getByLabel('显示名称', { exact: true }).fill(name);
    await admin.getByLabel('初始密码', { exact: true }).fill(password);
    await admin.getByLabel('账号角色', { exact: true }).first().selectOption(role);
    await admin.getByRole('button', { name: '创建账号', exact: true }).click();
    await admin.getByRole('status').filter({ hasText: `账号 ${username} 已创建` }).waitFor();
  }
  await noOverflow(admin, '桌面账号管理');
  await admin.screenshot({ path: path.join(root, 'design/admin-desktop.png'), fullPage: true });
  pass('管理员通过页面创建不同角色的账号');
  const editorContext = await browser.newContext({ viewport: { width: 1487, height: 1058 } });
  const editor = await editorContext.newPage(); observe(editor);
  await login(editor, 'qa_editor');
  assert.equal(await editor.getByRole('link', { name: '账号管理', exact: true }).count(), 0);
  await editor.getByLabel('选择知识库资料').setInputFiles({ name: '权限验收.txt', mimeType: 'text/plain', buffer: Buffer.from('青蓝书签：这是一段用于核对账号权限和共享持久化的测试原文。') });
  await editor.getByText('已保存 · 共享', { exact: true }).waitFor();
  await editor.reload();
  await editor.getByRole('button', { name: '权限验收.txt', exact: true }).waitFor();
  await editor.getByRole('button', { name: '权限验收.txt', exact: true }).click();
  await editor.getByText('青蓝书签：这是一段用于核对账号权限和共享持久化的测试原文。', { exact: true }).waitFor();
  await editor.keyboard.press('Escape');
  await editor.getByRole('textbox', { name: '向中药资料提问' }).fill('青蓝书签');
  await editor.getByRole('button', { name: '发送', exact: true }).click();
  await editor.getByText('未调用 AI', { exact: false }).first().waitFor();
  await editor.screenshot({ path: path.join(root, 'design/editor-workspace.png'), fullPage: true });
  pass('编辑员上传文本、刷新持久化、核对原文与摘录问答');
  const viewerContext = await browser.newContext({ viewport: { width: 1487, height: 1058 } });
  const viewer = await viewerContext.newPage(); observe(viewer);
  await login(viewer, 'qa_viewer');
  await viewer.getByRole('button', { name: '权限验收.txt', exact: true }).waitFor();
  assert.equal(await viewer.getByLabel('选择知识库资料').count(), 0);
  assert.equal(await viewer.getByRole('button', { name: '移除权限验收.txt', exact: true }).count(), 0);
  assert.equal(await viewer.getByRole('link', { name: '账号管理', exact: true }).count(), 0);
  const statuses = await viewer.evaluate(async () => {
    const headers = { 'Content-Type': 'application/json', 'X-CSRF-Protection': '1' };
    return [
      (await fetch('/api/users')).status,
      (await fetch('/api/documents', { method: 'POST', headers, body: JSON.stringify({ name: '越权.txt', content: '不允许保存' }) })).status,
    ];
  });
  assert.deepEqual(statuses, [403, 403]);
  await viewer.goto(origin + '/admin'); await viewer.waitForURL(origin + '/');
  await viewer.getByText('当前为普通用户', { exact: false }).waitFor();
  await viewer.screenshot({ path: path.join(root, 'design/viewer-workspace.png'), fullPage: true });
  pass('普通用户可读共享资料，不能绕过 UI 写资料或管理账号');
  const editorRow = admin.locator('.user-row').filter({ hasText: 'qa_editor' });
  await editorRow.getByRole('button', { name: '停用账号', exact: true }).click();
  await editorRow.getByText('已停用', { exact: true }).waitFor();
  await editor.reload(); await editor.waitForURL('**/login');
  pass('停用账号撤销已登录编辑员的会话');
  await editorRow.getByRole('button', { name: '启用账号', exact: true }).click();
  await editorRow.getByText('正常', { exact: true }).waitFor();
  await login(editor, 'qa_editor');
  await editor.getByRole('button', { name: '移除权限验收.txt', exact: true }).click();
  await editor.getByRole('button', { name: '权限验收.txt', exact: true }).waitFor({ state: 'detached' });
  await viewer.getByRole('button', { name: '刷新共享资料', exact: true }).click();
  await viewer.getByRole('button', { name: '权限验收.txt', exact: true }).waitFor({ state: 'detached' });
  pass('启用账号后重新登录，资料移除对其他用户可见');
  await viewer.getByRole('link', { name: /验收普通用户/ }).click();
  await viewer.getByLabel('原密码', { exact: true }).fill(password);
  await viewer.getByLabel('新密码', { exact: true }).fill(replacement);
  await viewer.getByLabel('确认新密码', { exact: true }).fill(replacement);
  await viewer.getByRole('button', { name: '修改密码并重新登录', exact: true }).click();
  await viewer.waitForURL('**/login');
  await login(viewer, 'qa_viewer', replacement);
  await viewer.getByRole('button', { name: '退出登录', exact: true }).click();
  await viewer.waitForURL('**/login');
  await viewer.goBack(); await viewer.waitForURL('**/login');
  pass('个人改密、使用新密码登录、退出后返回受保护页');
  const mobileContext = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  const mobile = await mobileContext.newPage(); observe(mobile);
  await mobile.goto(origin + '/login'); await noOverflow(mobile, '手机登录');
  await mobile.screenshot({ path: path.join(root, 'design/login-mobile.png'), fullPage: true });
  await login(mobile, 'qa_viewer', replacement);
  await noOverflow(mobile, '手机知识库');
  await mobile.getByRole('button', { name: '查看资料', exact: true }).click();
  await mobile.getByText('当前为普通用户', { exact: false }).waitFor();
  await mobile.keyboard.press('Escape');
  await mobile.getByRole('button', { name: '打开导航', exact: true }).click();
  await mobile.getByRole('button', { name: '退出登录', exact: true }).waitFor({ state: 'visible' });
  await mobile.keyboard.press('Escape');
  await mobile.screenshot({ path: path.join(root, 'design/viewer-mobile.png'), fullPage: true });
  await mobile.goto(origin + '/login');
  // Use a fresh mobile context to inspect administrator layout without cross-account state.
  const mobileAdminContext = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  const mobileAdmin = await mobileAdminContext.newPage(); observe(mobileAdmin);
  await login(mobileAdmin, 'qa_admin');
  await mobileAdmin.goto(origin + '/admin');
  await mobileAdmin.getByRole('heading', { name: '账号与权限管理' }).waitFor();
  await mobileAdmin.getByText('验收编辑员', { exact: false }).waitFor();
  await noOverflow(mobileAdmin, '手机账号管理');
  await mobileAdmin.screenshot({ path: path.join(root, 'design/admin-mobile.png'), fullPage: true });
  await mobileAdmin.setViewportSize({ width: 768, height: 1024 });
  await noOverflow(mobileAdmin, '平板账号管理');
  pass('390px 手机登录、只读资料、导航抽屉、管理员布局及 768px 平板布局');
  assert.deepEqual(errors, [], '浏览器未处理异常');
  pass('无浏览器未处理异常');
  await writeFile(path.join(root, 'design/auth-qa-result.json'), JSON.stringify({ date: '2026-10-27', status: 'passed', desktop: '1487x1058', mobile: '390x844', tablet: '768x1024', flows: 9, pageErrors: errors }, null, 2));
} finally {
  if (browser) await browser.close();
  for (const child of processes.reverse()) {
    try { execFileSync('taskkill', ['/PID', String(child.pid), '/T', '/F'], { windowsHide: true, stdio: 'ignore' }); } catch {}
  }
}
