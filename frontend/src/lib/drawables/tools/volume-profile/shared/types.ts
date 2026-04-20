export interface VolumeProfileBin {
  price: number;
  upVol: number;
  downVol: number;
}

export interface VolumeProfileResponse {
  rowSize: number;
  priceMin: number;
  priceMax: number;
  bins: VolumeProfileBin[];
  poc: number;
  vah: number;
  val: number;
  source: 'candle-distribution' | 'fine-grained';
}
