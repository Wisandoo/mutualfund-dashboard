'use client';

import { useEffect, useState } from 'react';
import { DjangoAPIResponse } from '@/types/ffs';
import { 
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, 
  RadialBarChart, RadialBar, PolarAngleAxis 
} from 'recharts';

export default function Home() {
  const [ffsList, setFfsList] = useState<DjangoAPIResponse[]>([]);
  const [selectedFund, setSelectedFund] = useState<DjangoAPIResponse | null>(null);
  const [loading, setLoading] = useState(true);
  
  // --- STATE FILTERING ---
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedMI, setSelectedMI] = useState<string>("");
  const [selectedType, setSelectedType] = useState<string>("");
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [selectedCurrency, setSelectedCurrency] = useState<string>("");

  useEffect(() => {
    // Fetch data dari Django Backend
    fetch('http://127.0.0.1:8000/api/ffs/')
      .then((res) => res.json())
      .then((data: DjangoAPIResponse[]) => {
        setFfsList(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Gagal mengambil data API:', err);
        setLoading(false);
      });
  }, []);

  // Helper untuk mendapatkan nama MI
  const getMI = (productCode: string, productName: string) => {
    const lowerCode = productCode?.toLowerCase() || "";
    const lowerName = productName?.toLowerCase() || "";
    if (lowerCode.includes('sucor') || lowerName.includes('sucor')) return 'Sucorinvest';
    if (lowerCode.includes('sya') || lowerName.includes('syailendra')) return 'Syailendra';
    if (lowerCode.includes('uob') || lowerName.includes('uob')) return 'UOB';
    return 'Lainnya';
  };

  // Helper untuk Tingkat Risiko
  const getRiskLevel = (type: string) => {
    switch(type?.toUpperCase()) {
      case 'SAHAM': return { label: 'Risiko Sangat Tinggi', color: 'text-red-500' };
      case 'CAMPURAN': return { label: 'Risiko Sedang', color: 'text-orange-500' };
      case 'PENDAPATAN TETAP': return { label: 'Risiko Sedang', color: 'text-orange-500' };
      case 'PASAR UANG': return { label: 'Risiko Sangat Rendah', color: 'text-green-500' };
      default: return { label: 'Risiko Sedang', color: 'text-orange-500' };
    }
  };

  if (loading) return <div className="flex h-screen items-center justify-center font-semibold">Memuat Data dari Django...</div>;

  // ============================================================================
  // TAMPILAN 1: DASHBOARD FUND FACT SHEET (DETAIL)
  // ============================================================================
  if (selectedFund) {
    const fundDetails = selectedFund.data;

    return (
      <main className="min-h-screen bg-gray-50 p-8 text-gray-800">
        <div className="mx-auto max-w-7xl space-y-6">
          
          <button 
            onClick={() => setSelectedFund(null)}
            className="flex items-center text-sm font-semibold text-blue-600 hover:text-blue-800 transition-colors"
          >
            &larr; Kembali ke Daftar Produk
          </button>

          <div className="flex flex-col justify-between gap-4 border-b pb-6 sm:flex-row sm:items-end">
            <div>
              <h1 className="text-3xl font-bold tracking-tight text-gray-900">Dashboard Fund Fact Sheet</h1>
              <p className="text-sm text-gray-500 mt-1">Analisis portofolio Manajer Investasi berbasis data KSEI & Pefindo</p>
            </div>
            <div className="rounded-lg border border-gray-300 bg-white px-4 py-2.5 shadow-sm text-gray-700 font-medium">
              {fundDetails.productName || selectedFund.product_code} ({fundDetails.ffsDate})
            </div>
          </div>

          <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
            <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-100">
              <p className="text-sm font-medium text-gray-500">Total AUM / Dana Kelolaan</p>
              <p className="mt-2 text-2xl font-bold text-blue-600">
                {fundDetails.currency === 'USD' ? '$ ' : 'Rp '}
                {fundDetails.aum ? fundDetails.aum.toLocaleString(fundDetails.currency === 'USD' ? 'en-US' : 'id-ID') : '0'}
              </p>
            </div>
            <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-100">
              <p className="text-sm font-medium text-gray-500">Jenis Reksa Dana</p>
              <p className="mt-2 text-2xl font-bold text-emerald-600 uppercase">{fundDetails.mfType || 'CAMPURAN'}</p>
            </div>
            <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-100">
              <p className="text-sm font-medium text-gray-500">Tanggal Laporan (As of)</p>
              <p className="mt-2 text-2xl font-bold text-amber-600">{fundDetails.ffsDate}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {/* Alokasi Aset */}
            <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-200">
              <h3 className="mb-6 text-lg font-bold text-gray-900 flex items-center gap-2">
                 <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z"></path><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z"></path></svg>
                 Alokasi Aset
              </h3>
              
              <div className="relative h-56 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <RadialBarChart 
                    cx="50%" cy="50%" innerRadius="50%" outerRadius="100%" barSize={16} 
                    startAngle={90} endAngle={-270}
                    data={(fundDetails.portfolioAllocations?.length ? [...fundDetails.portfolioAllocations] : [{ name: "Belum ada data", percentage: 100 }])
                      .sort((a, b) => a.percentage - b.percentage)
                      .map((item, index) => ({
                        ...item,
                        fill: index === 0 ? '#3b82f6' : '#22c55e'
                      }))} 
                  >
                    <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
                    <RadialBar background={{ fill: '#f3f4f6' }} dataKey="percentage" cornerRadius={10} />
                    <Tooltip formatter={(value) => [`${value}%`, 'Porsi']} />
                  </RadialBarChart>
                </ResponsiveContainer>
                
                <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-2 text-xs text-gray-400">0%</div>
                <div className="absolute bottom-4 right-1/4 translate-x-4 text-xs text-gray-400">50%</div>
                <div className="absolute top-1/2 left-1/4 -translate-x-4 -translate-y-1/2 text-xs text-gray-400">100%</div>
              </div>

              <div className="mt-4 space-y-3 border-b border-gray-100 pb-5">
                {(fundDetails.portfolioAllocations?.length ? [...fundDetails.portfolioAllocations] : [{ name: "Data Tidak Tersedia", percentage: 0 }])
                  .sort((a, b) => b.percentage - a.percentage)
                  .map((item, index) => (
                  <div key={index} className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className={`h-4 w-4 rounded-full ${index === 0 ? 'bg-green-500' : 'bg-blue-500'}`}></span>
                      <span className="text-gray-700">{item.name}</span>
                    </div>
                    <span className="font-semibold text-gray-900">{item.percentage}%</span>
                  </div>
                ))}
              </div>
              <div className="pt-4 text-center text-sm font-medium text-gray-600">
                Sumber: <a 
                  href={`/ffs_output/${fundDetails.productCode}_FS_${fundDetails.ffsPeriod}.pdf`} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-teal-500 underline decoration-teal-500/30 underline-offset-4 hover:text-teal-600 transition-colors"
                >
                  Fund Fact Sheet {fundDetails.ffsDate}
                </a>
              </div>
            </div>

            {/* Top 10 Efek */}
            <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-200">
              <h3 className="mb-6 text-lg font-bold text-gray-900">
                Top 10 Efek ({fundDetails.ffsPeriod?.replace('_', '-')})
              </h3>
              
              <div className="flex items-center justify-between border-b-2 border-gray-100 pb-3 text-sm font-semibold text-gray-900">
                <div className="flex items-center gap-1">
                  Nama Emiten / Efek <span className="text-gray-400">↕</span>
                </div>
                <div className="flex items-center gap-1 text-blue-500">
                  Porsi <span>↓</span>
                </div>
              </div>

              <div className="mt-2 divide-y divide-gray-100 h-80 overflow-y-auto pr-2 custom-scrollbar">
                {fundDetails.topHoldings?.map((holding: any, index: number) => (
                  <div key={index} className="flex items-center justify-between py-4 group">
                    <p className="text-sm font-medium text-gray-700 w-3/4 pr-4 leading-relaxed group-hover:text-blue-600 transition-colors">
                      {holding.name.toUpperCase()}
                    </p>
                    <div className="flex items-center gap-3 text-sm font-bold text-gray-900 w-1/4 justify-end">
                      {holding.percentage}%
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </main>
    );
  }

  // ============================================================================
  // TAMPILAN 2: HALAMAN UTAMA (LIST PRODUK & FILTER)
  // ============================================================================
  
  // Fungsi Multi-Filtering dinamis (MI, Tipe, Kategori, Mata Uang, & Search)
  const filteredList = ffsList.filter((fund) => {
    const data = fund.data;
    
    // 1. Filter Pencarian Text
    const nameMatch = (data.productName || "").toLowerCase().includes(searchQuery.toLowerCase());
    
    // 2. Filter Manager Investasi
    const miMatch = selectedMI === "" || getMI(fund.product_code, data.productName || "") === selectedMI;
    
    // 3. Filter Jenis Produk
    let fundType = data.mfType?.toUpperCase() || "";
    if (fundType === "EKUITAS") fundType = "SAHAM";
    if (fundType === "SUKUK") fundType = "PENDAPATAN TETAP"; 
    const typeMatch = selectedType === "" || fundType === selectedType;

    // 4. Filter Kategori (Syariah vs Konvensional)
    const isSyariah = (data.productName || "").toLowerCase().includes('sharia') || 
                      (data.productName || "").toLowerCase().includes('syariah') ||
                      data.mfType?.toUpperCase() === 'SUKUK';
    const catMatch = selectedCategory === "" || 
                     (selectedCategory === "SYARIAH" && isSyariah) || 
                     (selectedCategory === "KONVENSIONAL" && !isSyariah);

    // 5. Filter Mata Uang
    const currMatch = selectedCurrency === "" || data.currency === selectedCurrency;

    return nameMatch && miMatch && typeMatch && catMatch && currMatch;
  });

  // Komponen UI Pill untuk Filter
  const FilterPill = ({ label, active = false, onClick }: { label: string, active?: boolean, onClick?: () => void }) => (
    <button 
      onClick={onClick}
      className={`px-4 py-2 rounded-full border text-sm font-medium transition-all w-full text-center
        ${active 
          ? 'bg-blue-700 text-white border-blue-700 shadow-md' 
          : 'bg-white text-blue-700 border-blue-600 hover:bg-blue-50'}`}
    >
      {label}
    </button>
  );

  return (
    <div className="flex min-h-screen bg-gray-50">
      
      {/* SIDEBAR FILTER */}
      <aside className="w-80 bg-white border-r border-gray-200 p-6 flex flex-col gap-8 flex-shrink-0">
        
        {/* MI Filter */}
        <div>
          <button 
            onClick={() => {
              setSelectedMI("");
              setSelectedType("");
              setSelectedCategory("");
              setSelectedCurrency("");
            }}
            className="w-full py-3 px-4 bg-gray-50 border border-gray-300 text-gray-700 font-bold rounded-lg hover:bg-gray-100 transition-colors mb-4 italic"
          >
            {selectedMI === "" && selectedType === "" && selectedCategory === "" && selectedCurrency === "" 
              ? "Semua Manager Investasi" 
              : `Reset: Tampilkan Semua`}
          </button>
          
          <div className="flex flex-col gap-2">
             <FilterPill label="Sucorinvest Asset Mgt" active={selectedMI === "Sucorinvest"} onClick={() => setSelectedMI(selectedMI === "Sucorinvest" ? "" : "Sucorinvest")} />
             <FilterPill label="Syailendra Capital" active={selectedMI === "Syailendra"} onClick={() => setSelectedMI(selectedMI === "Syailendra" ? "" : "Syailendra")} />
             <FilterPill label="UOB Asset Management" active={selectedMI === "UOB"} onClick={() => setSelectedMI(selectedMI === "UOB" ? "" : "UOB")} />
          </div>
        </div>

        {/* Jenis Produk */}
        <div>
          <h3 className="text-sm font-bold text-gray-600 mb-3">Jenis Produk</h3>
          <div className="grid grid-cols-2 gap-2">
            <FilterPill label="Pasar Uang" active={selectedType === "PASAR UANG"} onClick={() => setSelectedType(selectedType === "PASAR UANG" ? "" : "PASAR UANG")} />
            <FilterPill label="Pendapatan Tetap" active={selectedType === "PENDAPATAN TETAP"} onClick={() => setSelectedType(selectedType === "PENDAPATAN TETAP" ? "" : "PENDAPATAN TETAP")} />
            <FilterPill label="Campuran" active={selectedType === "CAMPURAN"} onClick={() => setSelectedType(selectedType === "CAMPURAN" ? "" : "CAMPURAN")} />
            <FilterPill label="Saham" active={selectedType === "SAHAM"} onClick={() => setSelectedType(selectedType === "SAHAM" ? "" : "SAHAM")} />
            <FilterPill label="Indeks" active={selectedType === "INDEKS"} onClick={() => setSelectedType(selectedType === "INDEKS" ? "" : "INDEKS")} />
          </div>
        </div>

        {/* Kategori Produk */}
        <div>
          <h3 className="text-sm font-bold text-gray-600 mb-3">Kategori Produk</h3>
          <div className="grid grid-cols-2 gap-2">
            <FilterPill label="Konvensional" active={selectedCategory === "KONVENSIONAL"} onClick={() => setSelectedCategory(selectedCategory === "KONVENSIONAL" ? "" : "KONVENSIONAL")} />
            <FilterPill label="Syariah" active={selectedCategory === "SYARIAH"} onClick={() => setSelectedCategory(selectedCategory === "SYARIAH" ? "" : "SYARIAH")} />
          </div>
        </div>

        {/* Mata Uang */}
        <div>
          <h3 className="text-sm font-bold text-gray-600 mb-3">Mata Uang</h3>
          <div className="grid grid-cols-2 gap-2">
            <FilterPill label="IDR" active={selectedCurrency === "IDR"} onClick={() => setSelectedCurrency(selectedCurrency === "IDR" ? "" : "IDR")} />
            <FilterPill label="USD" active={selectedCurrency === "USD"} onClick={() => setSelectedCurrency(selectedCurrency === "USD" ? "" : "USD")} />
          </div>
        </div>
      </aside>

      {/* MAIN CONTENT (List Produk) */}
      <main className="flex-1 p-8">
        
        {/* Search Bar Saja (Elemen Sorting Dihapus Sesuai Permintaan) */}
        <div className="mb-6 flex items-center justify-between border-b border-gray-200 pb-4">
           <div className="relative w-full max-w-md">
              <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
              <input 
                type="text" 
                placeholder="Cari nama produk..." 
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border-none bg-transparent focus:ring-0 text-gray-700 italic placeholder-gray-400" 
              />
           </div>
        </div>

        {/* List Data Produk */}
        <div className="space-y-4">
          {filteredList.map((fund) => {
            const risk = getRiskLevel(fund.data.mfType);
            const aumValue = fund.data.aum;
            const currency = fund.data.currency === 'USD' ? '$' : 'Rp';
            
            // Format AUM Singkat (Triliun/Miliar)
            let aumFormatted = "0";
            if (aumValue >= 1e12) aumFormatted = `${currency}${(aumValue / 1e12).toFixed(1).replace('.0','')} triliun`;
            else if (aumValue >= 1e9) aumFormatted = `${currency}${(aumValue / 1e9).toFixed(0)} miliar`;
            else aumFormatted = `${currency}${(aumValue / 1e6).toFixed(0)} juta`;

            return (
              <div key={fund.id} className="flex items-center justify-between p-5 bg-white rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
                
                {/* Kolom 1: Logo & Nama */}
                <div className="flex items-center gap-4 w-1/2 pr-4">
                  <div className="w-12 h-12 rounded-full border border-gray-200 bg-gray-50 flex items-center justify-center flex-shrink-0 text-[10px] font-bold text-gray-400 text-center">
                    {getMI(fund.product_code, fund.data.productName || "UKN")}
                  </div>
                  <div>
                    <div className="text-xs font-medium text-gray-700 italic mb-1">
                      {fund.data.mfType?.toUpperCase() || 'CAMPURAN'} - <span className={risk.color}>{risk.label}</span>
                    </div>
                    <h2 className="text-lg font-bold text-gray-900">{fund.data.productName}</h2>
                  </div>
                </div>

                {/* Kolom 2: Min Beli & AUM */}
                <div className="flex items-center justify-between w-1/4 px-4 border-l border-gray-100">
                   <div className="flex flex-col">
                     <span className="text-[11px] text-gray-400 italic">Min. Pembelian</span>
                     <span className="text-sm font-semibold text-gray-800 italic">Rp100 ribu</span>
                   </div>
                   <div className="flex flex-col">
                     <span className="text-[11px] text-gray-400 italic">Total AUM</span>
                     <span className="text-sm font-semibold text-gray-800 italic">{aumFormatted}</span>
                   </div>
                </div>

                {/* Kolom 3: Action Buttons (Beli Dihapus Sesuai Permintaan) */}
                <div className="flex items-center justify-end w-1/4 pl-4 border-l border-gray-100">
                  <button 
                    onClick={() => setSelectedFund(fund)}
                    className="px-6 py-2.5 text-sm font-bold text-blue-700 border-2 border-blue-600 rounded-full hover:bg-blue-50 transition w-full max-w-[200px]"
                  >
                    Informasi Produk
                  </button>
                </div>

              </div>
            );
          })}
          
          {filteredList.length === 0 && (
            <div className="text-center py-20 text-gray-500 font-medium">
              Tidak ada produk yang sesuai dengan filter Anda.
            </div>
          )}
        </div>

      </main>
    </div>
  );
}