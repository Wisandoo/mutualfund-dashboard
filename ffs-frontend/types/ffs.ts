export interface HoldingData {
  name: string;
  percentage: number;
  code?: string;
  type?: string;
  rating?: string | null;
  maturityDate?: string | null;
  couponFrequency?: string | null;
}

export interface AllocationData {
  name: string;
  percentage: number;
}

export interface FFSData {
  productName: string;
  productCode: string;
  ffsDate: string;
  ffsPeriod: string;
  aum: number;
  totalAum: number;
  mfType: string;
  currency: string;
  topHoldings: HoldingData[];
  portfolioAllocations: AllocationData[];
}

export interface DjangoAPIResponse {
  id?: number;
  product_code: string;
  ffs_date: string;
  data: FFSData;
  aum: number;
}