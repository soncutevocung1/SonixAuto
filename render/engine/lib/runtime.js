// Sonix runtime: nap vao moi composition HTML.
// Cung cap: spring vat ly, noi suy, easing, va hop dong renderFrame(frame).
(function () {
  // ---- Spring vat ly (dao dong tat dan) ----
  // Tich phan so voi buoc 1ms => ket qua giong nhau tren moi may.
  const cache = new Map();
  function springCurve(cfg) {
    const { stiffness = 170, damping = 18, mass = 1, velocity = 0 } = cfg;
    const key = `${stiffness}|${damping}|${mass}|${velocity}`;
    if (cache.has(key)) return cache.get(key);
    const dt = 1 / 1000;
    const pts = [];
    let x = 0, v = velocity; // x: tien do 0 -> 1
    for (let i = 0; i <= 6000; i++) {
      pts.push(x);
      const a = (-stiffness * (x - 1) - damping * v) / mass;
      v += a * dt;
      x += v * dt;
    }
    cache.set(key, pts);
    return pts;
  }

  // spring({frame, fps, delay, from, to, config})
  function spring({ frame, fps, delay = 0, from = 0, to = 1, config = {} }) {
    const t = frame / fps - delay;
    if (t <= 0) return from;
    const pts = springCurve(config);
    const idx = Math.min(pts.length - 1, Math.round(t * 1000));
    return from + (to - from) * pts[idx];
  }

  // Thoi gian (giay) de lo xo "lang" han
  function springDuration(config = {}, eps = 0.004) {
    const pts = springCurve(config);
    for (let i = pts.length - 1; i > 0; i--) {
      if (Math.abs(pts[i] - 1) > eps) return (i + 1) / 1000;
    }
    return 0;
  }

  const ease = {
    linear: (t) => t,
    inOut: (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
    out: (t) => 1 - Math.pow(1 - t, 3),
    in: (t) => t * t * t,
  };

  // interpolate(x, [a,b,...], [c,d,...], {clamp, easing})
  function interpolate(x, input, output, opt = {}) {
    const { clamp = true, easing = ease.linear } = opt;
    let i = 1;
    while (i < input.length - 1 && x > input[i]) i++;
    const a = input[i - 1], b = input[i];
    let t = (x - a) / (b - a || 1);
    if (clamp) t = Math.max(0, Math.min(1, t));
    t = easing(t);
    return output[i - 1] + (output[i] - output[i - 1]) * t;
  }

  // Nhieu ngau nhien co dinh theo seed (de hat/particle khong nhay khi render lai)
  function rand(seed) {
    let s = seed >>> 0 || 1;
    return () => {
      s ^= s << 13; s ^= s >>> 17; s ^= s << 5;
      return ((s >>> 0) % 100000) / 100000;
    };
  }

  // Doi tat ca <video data-sx-video> toi dung thoi diem, cho den khi khung hien
  async function seekVideos(sec) {
    const vids = [...document.querySelectorAll('video[data-sx-video]')];
    await Promise.all(vids.map((v) => new Promise((res) => {
      const start = parseFloat(v.dataset.start || '0');
      const rate = parseFloat(v.dataset.rate || '1');
      const target = Math.max(0, Math.min(v.duration - 0.01 || 0, start + (sec - parseFloat(v.dataset.at || '0')) * rate));
      if (Math.abs(v.currentTime - target) < 0.001) return res();
      v.addEventListener('seeked', () => requestAnimationFrame(() => res()), { once: true });
      v.currentTime = target;
    })));
  }

  // Lay URL anh cua video 'name' tai giay 'local' (tinh tu luc video bat dau hien)
  function mediaFrame(name, local) {
    const m = (window.SX.props.media || {})[name];
    if (!m) return '';
    if (m.url) return m.url;
    const fps = window.SX.fps;
    const i = Math.max(1, Math.min(m.frames.count, Math.floor(local * fps) + 1));
    return m.frames.base + String(i).padStart(5, '0') + '.jpg';
  }
  // Doi <img> sang anh moi va cho anh giai ma xong
  function setImg(img, url) {
    if (!url || img.getAttribute('src') === url) return Promise.resolve();
    img.src = url;
    return img.decode().catch(() => {});
  }

  window.SX = {
    mediaFrame, setImg,
    props: window.__SX_PROPS__ || {},
    fps: 30,
    spring, springDuration, interpolate, ease, rand, seekVideos,
  };
})();
