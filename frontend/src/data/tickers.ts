export interface TickerInfo {
  name: string
  description: string
  exchange: 'NASDAQ' | 'NYSE'
}

export const TICKER_INFO: Record<string, TickerInfo> = {
  // AI
  NVDA:  { name: 'NVIDIA Corporation',         exchange: 'NASDAQ', description: 'Designs GPUs and AI chips; dominant supplier for data center AI training and inference.' },
  MSFT:  { name: 'Microsoft Corporation',       exchange: 'NASDAQ', description: 'Cloud computing (Azure), productivity software (Office 365), and AI services (Copilot).' },
  GOOGL: { name: 'Alphabet Inc.',               exchange: 'NASDAQ', description: 'Google Search, YouTube, Google Cloud, and AI research (Gemini).' },
  META:  { name: 'Meta Platforms Inc.',         exchange: 'NASDAQ', description: 'Facebook, Instagram, WhatsApp, and investments in virtual/augmented reality.' },
  AMZN:  { name: 'Amazon.com Inc.',             exchange: 'NASDAQ', description: 'E-commerce marketplace, AWS cloud platform, and digital advertising.' },
  AMD:   { name: 'Advanced Micro Devices',      exchange: 'NASDAQ', description: 'CPUs and GPUs for PC, server, and AI markets; major competitor to Intel and NVIDIA.' },
  ORCL:  { name: 'Oracle Corporation',          exchange: 'NYSE',   description: 'Enterprise database software, ERP cloud applications, and cloud infrastructure.' },
  CRM:   { name: 'Salesforce Inc.',             exchange: 'NYSE',   description: 'Customer relationship management (CRM) software and enterprise cloud platform.' },
  PLTR:  { name: 'Palantir Technologies',       exchange: 'NYSE',   description: 'AI-driven data analytics platforms for government intelligence and enterprise operations.' },
  SOUN:  { name: 'SoundHound AI Inc.',          exchange: 'NASDAQ', description: 'Voice AI and conversational intelligence platform for automotive, hospitality, and IoT.' },

  // Cloud
  SNOW:  { name: 'Snowflake Inc.',              exchange: 'NYSE',   description: 'Cloud data warehouse and analytics platform enabling cross-cloud data sharing.' },
  DDOG:  { name: 'Datadog Inc.',                exchange: 'NASDAQ', description: 'Cloud observability, monitoring, security, and log management platform.' },
  NET:   { name: 'Cloudflare Inc.',             exchange: 'NYSE',   description: 'Global CDN, DDoS protection, zero-trust security, and edge computing services.' },
  ZS:    { name: 'Zscaler Inc.',                exchange: 'NASDAQ', description: 'Cloud-native zero-trust cybersecurity platform; secures remote access without VPN.' },
  MDB:   { name: 'MongoDB Inc.',                exchange: 'NASDAQ', description: 'NoSQL document database platform for modern application development.' },
  HUBS:  { name: 'HubSpot Inc.',                exchange: 'NYSE',   description: 'CRM, marketing automation, and sales software primarily serving SMBs.' },

  // Networking
  CSCO:  { name: 'Cisco Systems',               exchange: 'NASDAQ', description: 'Enterprise networking hardware, software, and cybersecurity solutions worldwide.' },
  ANET:  { name: 'Arista Networks',             exchange: 'NYSE',   description: 'High-speed cloud networking switches and EOS software for hyperscale data centers.' },
  JNPR:  { name: 'Juniper Networks',            exchange: 'NYSE',   description: 'Enterprise networking routers, switches, and AI-driven security.' },
  CIEN:  { name: 'Ciena Corporation',           exchange: 'NYSE',   description: 'Optical networking and wavelength division multiplexing for telecoms and hyperscalers.' },
  EXTR:  { name: 'Extreme Networks',            exchange: 'NASDAQ', description: 'Cloud-managed Wi-Fi, switching, and analytics for enterprise and education.' },
  CALX:  { name: 'Calix Inc.',                  exchange: 'NYSE',   description: 'Cloud and software platforms helping broadband service providers grow their networks.' },
  LITE:  { name: 'Lumentum Holdings',           exchange: 'NASDAQ', description: 'Optical and photonic products for networking, 3D sensing, and industrial lasers.' },
  VIAV:  { name: 'Viavi Solutions',             exchange: 'NASDAQ', description: 'Network test, monitoring equipment, and optical security products.' },
  INFN:  { name: 'Infinera Corporation',        exchange: 'NASDAQ', description: 'Optical transport networking solutions for long-haul and submarine cables.' },
  RBBN:  { name: 'Ribbon Communications',       exchange: 'NASDAQ', description: 'Cloud and edge IP communications software and security solutions.' },

  // Alternative Energy
  ENPH:  { name: 'Enphase Energy',              exchange: 'NASDAQ', description: 'Microinverter systems, home batteries, and energy management software for residential solar.' },
  FSLR:  { name: 'First Solar Inc.',            exchange: 'NASDAQ', description: 'Manufactures thin-film cadmium telluride solar panels for utility-scale projects.' },
  RUN:   { name: 'Sunrun Inc.',                 exchange: 'NASDAQ', description: 'Largest U.S. residential solar and home battery company via lease and ownership models.' },
  NOVA:  { name: 'Sunnova Energy International',exchange: 'NYSE',   description: 'Residential solar energy and battery storage services across the U.S. and territories.' },
  SEDG:  { name: 'SolarEdge Technologies',      exchange: 'NASDAQ', description: 'DC-optimised inverter systems and power electronics for solar installations.' },
  PLUG:  { name: 'Plug Power Inc.',             exchange: 'NASDAQ', description: 'Green hydrogen ecosystem: electrolysers, fuel cells, and liquefaction for industrial use.' },
  BE:    { name: 'Bloom Energy',                exchange: 'NYSE',   description: 'Solid oxide fuel cells providing on-site clean power for data centers and industry.' },
  ARRY:  { name: 'Array Technologies Inc.',     exchange: 'NASDAQ', description: 'Single-axis solar tracking systems that increase energy yield for utility-scale farms.' },
  CSIQ:  { name: 'Canadian Solar Inc.',         exchange: 'NASDAQ', description: 'Global manufacturer of solar modules and developer of utility-scale energy projects.' },
  JKS:   { name: 'JinkoSolar Holding',          exchange: 'NYSE',   description: 'One of the world\'s largest solar module manufacturers by shipment volume.' },

  // Gas / Oil
  XOM:   { name: 'ExxonMobil Corporation',      exchange: 'NYSE',   description: 'Integrated oil and gas supermajor spanning upstream, downstream, and chemicals.' },
  CVX:   { name: 'Chevron Corporation',          exchange: 'NYSE',   description: 'Integrated energy company with major LNG, oil sands, and deepwater operations.' },
  COP:   { name: 'ConocoPhillips',               exchange: 'NYSE',   description: 'Exploration and production company focused on low-cost, low-carbon oil and gas.' },
  EOG:   { name: 'EOG Resources',                exchange: 'NYSE',   description: 'Premier U.S. shale oil and gas E&P company in Permian, Eagle Ford, and Bakken.' },
  PXD:   { name: 'Pioneer Natural Resources',    exchange: 'NYSE',   description: 'Permian Basin pure-play E&P; largest acreage holder in the Midland Basin.' },
  DVN:   { name: 'Devon Energy',                 exchange: 'NYSE',   description: 'Oil and gas exploration focused on U.S. unconventional plays and fixed-plus-variable dividends.' },
  HAL:   { name: 'Halliburton Company',          exchange: 'NYSE',   description: 'Global oilfield services leader in drilling, completion, and production.' },
  SLB:   { name: 'SLB (Schlumberger)',           exchange: 'NYSE',   description: 'World\'s largest oilfield services company; technology, digital, and integration services.' },
  BKR:   { name: 'Baker Hughes Company',         exchange: 'NASDAQ', description: 'Oilfield equipment and services; also industrial technology for energy transition.' },
  MPC:   { name: 'Marathon Petroleum',           exchange: 'NYSE',   description: 'U.S. petroleum refining, retail fuel, and pipeline midstream operations.' },

  // Finance
  JPM:   { name: 'JPMorgan Chase & Co.',         exchange: 'NYSE',   description: 'Largest U.S. bank by assets; consumer banking, investment banking, and asset management.' },
  BAC:   { name: 'Bank of America',              exchange: 'NYSE',   description: 'Consumer and commercial banking, wealth management via Merrill, and investment banking.' },
  WFC:   { name: 'Wells Fargo & Company',        exchange: 'NYSE',   description: 'Consumer and commercial banking focused on U.S. domestic lending and deposits.' },
  GS:    { name: 'The Goldman Sachs Group',      exchange: 'NYSE',   description: 'Leading investment bank in M&A advisory, trading, and asset management.' },
  MS:    { name: 'Morgan Stanley',               exchange: 'NYSE',   description: 'Investment banking, institutional securities, and wealth management (E*TRADE).' },
  C:     { name: 'Citigroup Inc.',               exchange: 'NYSE',   description: 'Global banking network serving corporates, governments, and institutions in 160+ countries.' },
  AXP:   { name: 'American Express Company',     exchange: 'NYSE',   description: 'Premium credit cards, charge cards, and financial services with strong rewards ecosystem.' },
  BLK:   { name: 'BlackRock Inc.',               exchange: 'NYSE',   description: 'World\'s largest asset manager with $10T+ AUM; known for iShares ETFs and Aladdin risk.' },
  SCHW:  { name: 'Charles Schwab',               exchange: 'NYSE',   description: 'Discount brokerage, banking, and investment advisory services; acquired TD Ameritrade.' },
  COF:   { name: 'Capital One Financial',        exchange: 'NYSE',   description: 'Tech-forward consumer credit card issuer and commercial banking services.' },
}

export function getTickerInfo(ticker: string): TickerInfo | null {
  return TICKER_INFO[ticker.toUpperCase()] ?? null
}

export function googleFinanceUrl(ticker: string): string {
  const info = getTickerInfo(ticker)
  const exchange = info?.exchange ?? 'NASDAQ'
  return `https://www.google.com/finance/quote/${ticker}:${exchange}`
}
