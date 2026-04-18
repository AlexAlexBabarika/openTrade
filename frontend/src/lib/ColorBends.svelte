<script lang="ts" module>
  export type ColorBendsProps = {
    colors?: string[];
    speed?: number;
    rotation?: number;
    autoRotate?: number;
    scale?: number;
    frequency?: number;
    warpStrength?: number;
    mouseInfluence?: number;
    parallax?: number;
    noise?: number;
    iterations?: number;
    intensity?: number;
    bandWidth?: number;
    transparent?: boolean;
    class?: string;
    style?: string;
  };
</script>

<script lang="ts">
  import { onMount } from 'svelte';

  const MAX_COLORS = 8;

  let {
    colors = [],
    speed = 0.2,
    rotation = 90,
    autoRotate = 0,
    scale = 2,
    frequency = 1,
    warpStrength = 1,
    mouseInfluence = 1,
    parallax = 0.5,
    noise = 0.25,
    iterations = 1,
    intensity = 1.5,
    bandWidth = 6,
    transparent = true,
    class: className = '',
    style: styleProp = '',
  }: ColorBendsProps = $props();

  let container = $state<HTMLDivElement | null>(null);

  type Ctx = {
    gl: WebGLRenderingContext;
    canvas: HTMLCanvasElement;
    program: WebGLProgram;
    locs: Record<string, WebGLUniformLocation | null>;
    colorsBuf: Float32Array;
    pointerTarget: [number, number];
    pointerCurrent: [number, number];
    startMs: number;
    lastMs: number;
  };
  let ctx: Ctx | null = null;

  function hexToRgb(hex: string): [number, number, number] {
    const h = hex.replace('#', '').trim();
    if (h.length === 3) {
      return [
        parseInt(h[0] + h[0], 16) / 255,
        parseInt(h[1] + h[1], 16) / 255,
        parseInt(h[2] + h[2], 16) / 255,
      ];
    }
    return [
      parseInt(h.slice(0, 2), 16) / 255,
      parseInt(h.slice(2, 4), 16) / 255,
      parseInt(h.slice(4, 6), 16) / 255,
    ];
  }

  function compile(gl: WebGLRenderingContext, type: number, src: string) {
    const s = gl.createShader(type)!;
    gl.shaderSource(s, src);
    gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
      console.error('ColorBends shader error:', gl.getShaderInfoLog(s));
      gl.deleteShader(s);
      throw new Error('shader compile failed');
    }
    return s;
  }

  const VERT = `
    attribute vec2 aPos;
    varying vec2 vUv;
    void main() {
      vUv = aPos * 0.5 + 0.5;
      gl_Position = vec4(aPos, 0.0, 1.0);
    }
  `;

  const FRAG = `
    precision highp float;
    #define MAX_COLORS ${MAX_COLORS}
    uniform vec2 uCanvas;
    uniform float uTime;
    uniform float uSpeed;
    uniform vec2 uRot;
    uniform int uColorCount;
    uniform vec3 uColors[MAX_COLORS];
    uniform int uTransparent;
    uniform float uScale;
    uniform float uFrequency;
    uniform float uWarpStrength;
    uniform vec2 uPointer;
    uniform float uMouseInfluence;
    uniform float uParallax;
    uniform float uNoise;
    uniform int uIterations;
    uniform float uIntensity;
    uniform float uBandWidth;
    varying vec2 vUv;

    void main() {
      float t = uTime * uSpeed;
      vec2 p = vUv * 2.0 - 1.0;
      p += uPointer * uParallax * 0.1;
      vec2 rp = vec2(p.x * uRot.x - p.y * uRot.y, p.x * uRot.y + p.y * uRot.x);
      vec2 q = vec2(rp.x * (uCanvas.x / uCanvas.y), rp.y);
      q /= max(uScale, 0.0001);
      q /= 0.5 + 0.2 * dot(q, q);
      q += 0.2 * cos(t) - 7.56;
      vec2 toward = (uPointer - rp);
      q += toward * uMouseInfluence * 0.2;

      for (int j = 0; j < 5; j++) {
        if (j >= uIterations - 1) break;
        vec2 rr = sin(1.5 * (q.yx * uFrequency) + 2.0 * cos(q * uFrequency));
        q += (rr - q) * 0.15;
      }

      vec3 col = vec3(0.0);
      float a = 1.0;

      if (uColorCount > 0) {
        vec2 s = q;
        vec3 sumCol = vec3(0.0);
        float cover = 0.0;
        for (int i = 0; i < MAX_COLORS; ++i) {
          if (i >= uColorCount) break;
          s -= 0.01;
          vec2 r = sin(1.5 * (s.yx * uFrequency) + 2.0 * cos(s * uFrequency));
          float m0 = length(r + sin(5.0 * r.y * uFrequency - 3.0 * t + float(i)) / 4.0);
          float kBelow = clamp(uWarpStrength, 0.0, 1.0);
          float kMix = pow(kBelow, 0.3);
          float gain = 1.0 + max(uWarpStrength - 1.0, 0.0);
          vec2 disp = (r - s) * kBelow;
          vec2 warped = s + disp * gain;
          float m1 = length(warped + sin(5.0 * warped.y * uFrequency - 3.0 * t + float(i)) / 4.0);
          float m = mix(m0, m1, kMix);
          float w = 1.0 - exp(-uBandWidth / exp(uBandWidth * m));
          sumCol += uColors[i] * w;
          cover = max(cover, w);
        }
        col = clamp(sumCol, 0.0, 1.0);
        a = uTransparent > 0 ? cover : 1.0;
      } else {
        vec2 s = q;
        for (int k = 0; k < 3; ++k) {
          s -= 0.01;
          vec2 r = sin(1.5 * (s.yx * uFrequency) + 2.0 * cos(s * uFrequency));
          float m0 = length(r + sin(5.0 * r.y * uFrequency - 3.0 * t + float(k)) / 4.0);
          float kBelow = clamp(uWarpStrength, 0.0, 1.0);
          float kMix = pow(kBelow, 0.3);
          float gain = 1.0 + max(uWarpStrength - 1.0, 0.0);
          vec2 disp = (r - s) * kBelow;
          vec2 warped = s + disp * gain;
          float m1 = length(warped + sin(5.0 * warped.y * uFrequency - 3.0 * t + float(k)) / 4.0);
          float m = mix(m0, m1, kMix);
          col[k] = 1.0 - exp(-uBandWidth / exp(uBandWidth * m));
        }
        a = uTransparent > 0 ? max(max(col.r, col.g), col.b) : 1.0;
      }

      col *= uIntensity;

      if (uNoise > 0.0001) {
        float n = fract(sin(dot(gl_FragCoord.xy + vec2(uTime), vec2(12.9898, 78.233))) * 43758.5453123);
        col += (n - 0.5) * uNoise;
        col = clamp(col, 0.0, 1.0);
      }

      vec3 rgb = (uTransparent > 0) ? col * a : col;
      gl_FragColor = vec4(rgb, a);
    }
  `;

  function setupUniforms(gl: WebGLRenderingContext, program: WebGLProgram) {
    const names = [
      'uCanvas',
      'uTime',
      'uSpeed',
      'uRot',
      'uColorCount',
      'uColors',
      'uTransparent',
      'uScale',
      'uFrequency',
      'uWarpStrength',
      'uPointer',
      'uMouseInfluence',
      'uParallax',
      'uNoise',
      'uIterations',
      'uIntensity',
      'uBandWidth',
    ];
    const locs: Record<string, WebGLUniformLocation | null> = {};
    for (const n of names) locs[n] = gl.getUniformLocation(program, n);
    return locs;
  }

  function uploadColors(c: Ctx) {
    const arr = (colors || []).filter(Boolean).slice(0, MAX_COLORS);
    c.colorsBuf.fill(0);
    for (let i = 0; i < arr.length; i++) {
      const [r, g, b] = hexToRgb(arr[i]);
      c.colorsBuf[i * 3] = r;
      c.colorsBuf[i * 3 + 1] = g;
      c.colorsBuf[i * 3 + 2] = b;
    }
    c.gl.useProgram(c.program);
    c.gl.uniform3fv(c.locs.uColors, c.colorsBuf);
    c.gl.uniform1i(c.locs.uColorCount, arr.length);
  }

  function uploadStaticUniforms(c: Ctx) {
    const gl = c.gl;
    gl.useProgram(c.program);
    gl.uniform1f(c.locs.uSpeed, speed);
    gl.uniform1f(c.locs.uScale, scale);
    gl.uniform1f(c.locs.uFrequency, frequency);
    gl.uniform1f(c.locs.uWarpStrength, warpStrength);
    gl.uniform1f(c.locs.uMouseInfluence, mouseInfluence);
    gl.uniform1f(c.locs.uParallax, parallax);
    gl.uniform1f(c.locs.uNoise, noise);
    gl.uniform1i(c.locs.uIterations, iterations);
    gl.uniform1f(c.locs.uIntensity, intensity);
    gl.uniform1f(c.locs.uBandWidth, bandWidth);
    gl.uniform1i(c.locs.uTransparent, transparent ? 1 : 0);
  }

  function resize(c: Ctx) {
    if (!container) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = Math.max(1, container.clientWidth);
    const h = Math.max(1, container.clientHeight);
    c.canvas.width = Math.floor(w * dpr);
    c.canvas.height = Math.floor(h * dpr);
    c.canvas.style.width = w + 'px';
    c.canvas.style.height = h + 'px';
    c.gl.viewport(0, 0, c.canvas.width, c.canvas.height);
    c.gl.useProgram(c.program);
    c.gl.uniform2f(c.locs.uCanvas, w, h);
  }

  onMount(() => {
    if (!container) return;
    const canvas = document.createElement('canvas');
    canvas.style.display = 'block';
    canvas.style.width = '100%';
    canvas.style.height = '100%';
    container.appendChild(canvas);

    const gl = canvas.getContext('webgl', {
      alpha: true,
      premultipliedAlpha: true,
      antialias: false,
      powerPreference: 'high-performance',
    });
    if (!gl) {
      console.warn('ColorBends: WebGL unavailable');
      return;
    }

    const vs = compile(gl, gl.VERTEX_SHADER, VERT);
    const fs = compile(gl, gl.FRAGMENT_SHADER, FRAG);
    const program = gl.createProgram()!;
    gl.attachShader(program, vs);
    gl.attachShader(program, fs);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      console.error('ColorBends link error:', gl.getProgramInfoLog(program));
      return;
    }

    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(
      gl.ARRAY_BUFFER,
      new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]),
      gl.STATIC_DRAW,
    );
    const aPos = gl.getAttribLocation(program, 'aPos');
    gl.enableVertexAttribArray(aPos);
    gl.vertexAttribPointer(aPos, 2, gl.FLOAT, false, 0, 0);

    gl.enable(gl.BLEND);
    gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
    gl.clearColor(0, 0, 0, 0);

    const locs = setupUniforms(gl, program);
    const now = performance.now();
    ctx = {
      gl,
      canvas,
      program,
      locs,
      colorsBuf: new Float32Array(MAX_COLORS * 3),
      pointerTarget: [0, 0],
      pointerCurrent: [0, 0],
      startMs: now,
      lastMs: now,
    };

    uploadStaticUniforms(ctx);
    uploadColors(ctx);
    resize(ctx);

    const ro =
      'ResizeObserver' in window ? new ResizeObserver(() => ctx && resize(ctx)) : null;
    if (ro) ro.observe(container);
    else window.addEventListener('resize', () => ctx && resize(ctx));

    const onPointer = (e: PointerEvent) => {
      if (!container) return;
      const rect = container.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / (rect.width || 1)) * 2 - 1;
      const y = -(((e.clientY - rect.top) / (rect.height || 1)) * 2 - 1);
      if (ctx) ctx.pointerTarget = [x, y];
    };
    container.addEventListener('pointermove', onPointer);

    let raf = 0;
    const loop = () => {
      if (!ctx) return;
      const nowMs = performance.now();
      const dt = (nowMs - ctx.lastMs) / 1000;
      ctx.lastMs = nowMs;
      const elapsed = (nowMs - ctx.startMs) / 1000;

      const [tx, ty] = ctx.pointerTarget;
      const [cx, cy] = ctx.pointerCurrent;
      const k = Math.min(1, dt * 8);
      ctx.pointerCurrent = [cx + (tx - cx) * k, cy + (ty - cy) * k];

      const deg = (rotation % 360) + autoRotate * elapsed;
      const rad = (deg * Math.PI) / 180;

      gl.useProgram(program);
      gl.uniform1f(locs.uTime, elapsed);
      gl.uniform2f(locs.uRot, Math.cos(rad), Math.sin(rad));
      gl.uniform2f(locs.uPointer, ctx.pointerCurrent[0], ctx.pointerCurrent[1]);

      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);

    return () => {
      cancelAnimationFrame(raf);
      ro?.disconnect();
      container?.removeEventListener('pointermove', onPointer);
      gl.deleteProgram(program);
      gl.deleteShader(vs);
      gl.deleteShader(fs);
      gl.deleteBuffer(buf);
      const ext = gl.getExtension('WEBGL_lose_context');
      ext?.loseContext();
      if (canvas.parentElement === container) container?.removeChild(canvas);
      ctx = null;
    };
  });

  // Live-update uniforms when props change.
  $effect(() => {
    if (!ctx) return;
    // Touch props to register dependencies.
    void speed;
    void scale;
    void frequency;
    void warpStrength;
    void mouseInfluence;
    void parallax;
    void noise;
    void iterations;
    void intensity;
    void bandWidth;
    void transparent;
    uploadStaticUniforms(ctx);
  });

  $effect(() => {
    if (!ctx) return;
    void colors;
    uploadColors(ctx);
  });
</script>

<div
  bind:this={container}
  class={'color-bends-container ' + className}
  style={styleProp}
></div>

<style>
  .color-bends-container {
    position: relative;
    width: 100%;
    height: 100%;
    overflow: hidden;
  }
</style>
