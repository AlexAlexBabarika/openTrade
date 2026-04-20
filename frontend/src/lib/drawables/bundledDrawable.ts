import type { RulerDrawable } from './tools/ruler/tool';
import type { AvpDrawable } from './tools/volume-profile/avp/tool';

/** Discriminated by `type`; geometry/params/style are narrowed per bundled tool. */
export type BundledDrawable = RulerDrawable | AvpDrawable;
