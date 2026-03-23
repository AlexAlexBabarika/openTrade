export interface HSVA {
  h: number; // 0–360
  s: number; // 0–1
  v: number; // 0–1
  a: number; // 0–1
}

/** Parse any CSS colour string (#RRGGBB, #RRGGBBAA, rgba(...)) into HSVA. */
export function cssColourToHsva(colour: string): HSVA {
  let r = 0,
    g = 0,
    b = 0,
    a = 1;

  const trimmed = colour.trim();

  if (trimmed.startsWith('#')) {
    const hex = trimmed.slice(1);
    if (hex.length >= 6) {
      r = parseInt(hex.slice(0, 2), 16);
      g = parseInt(hex.slice(2, 4), 16);
      b = parseInt(hex.slice(4, 6), 16);
      if (hex.length === 8) {
        a = parseInt(hex.slice(6, 8), 16) / 255;
      }
    } else {
      return { h: 0, s: 0, v: 0, a: 1 };
    }
  } else {
    const rgbaMatch = trimmed.match(
      /rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)(?:\s*,\s*([\d.]+))?\s*\)/,
    );
    if (rgbaMatch) {
      r = parseFloat(rgbaMatch[1]);
      g = parseFloat(rgbaMatch[2]);
      b = parseFloat(rgbaMatch[3]);
      a = rgbaMatch[4] !== undefined ? parseFloat(rgbaMatch[4]) : 1;
    } else {
      return { h: 0, s: 0, v: 0, a: 1 };
    }
  }

  if (isNaN(r) || isNaN(g) || isNaN(b) || isNaN(a)) {
    return { h: 0, s: 0, v: 0, a: 1 };
  }

  return { ...rgbToHsv(r, g, b), a };
}

function rgbToHsv(r: number, g: number, b: number): { h: number; s: number; v: number } {
  r /= 255;
  g /= 255;
  b /= 255;

  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const d = max - min;

  let h = 0;
  const s = max === 0 ? 0 : d / max;
  const v = max;

  if (d !== 0) {
    if (max === r) {
      h = ((g - b) / d + (g < b ? 6 : 0)) * 60;
    } else if (max === g) {
      h = ((b - r) / d + 2) * 60;
    } else {
      h = ((r - g) / d + 4) * 60;
    }
  }

  return { h, s, v };
}

function hsvToRgb(h: number, s: number, v: number): [number, number, number] {
  h = ((h % 360) + 360) % 360;
  const c = v * s;
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
  const m = v - c;

  let r = 0,
    g = 0,
    b = 0;

  if (h < 60) {
    r = c; g = x;
  } else if (h < 120) {
    r = x; g = c;
  } else if (h < 180) {
    g = c; b = x;
  } else if (h < 240) {
    g = x; b = c;
  } else if (h < 300) {
    r = x; b = c;
  } else {
    r = c; b = x;
  }

  return [
    Math.round((r + m) * 255),
    Math.round((g + m) * 255),
    Math.round((b + m) * 255),
  ];
}

/** Convert HSVA to hex string. #RRGGBB when alpha=1, #RRGGBBAA otherwise. */
export function hsvaToHex(hsva: HSVA): string {
  const [r, g, b] = hsvToRgb(hsva.h, hsva.s, hsva.v);
  const hex = '#' + [r, g, b].map((c) => c.toString(16).padStart(2, '0')).join('');

  if (hsva.a >= 1) return hex;

  const alphaByte = Math.round(hsva.a * 255);
  return hex + alphaByte.toString(16).padStart(2, '0');
}

/** Convert HSVA to CSS rgba() string (for use in style attributes). */
export function hsvaToRgba(hsva: HSVA): string {
  const [r, g, b] = hsvToRgb(hsva.h, hsva.s, hsva.v);
  return `rgba(${r}, ${g}, ${b}, ${+hsva.a.toFixed(2)})`;
}
