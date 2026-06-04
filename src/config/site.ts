export type SiteLink = {
	href: string;
	label: string;
};

export type SiteConfig = {
	name: string;
	title: string;
	description: string;
	siteUrl: string;
	email: string;
	locale: string;
	authorName: string;
	authorRole: string;
	keywords: string[];
	ogImage: string;
	navLinks: SiteLink[];
	extraPages: SiteLink[];
	legalLinks: SiteLink[];
	socialLinks: SiteLink[];
};

export const siteConfig: SiteConfig = {
	name: 'Maria',
	title: 'Maria | UX Designer Portfolio',
	description: 'A clean Astro portfolio template for UX designers and visual product thinkers.',
	// Replace this when reusing the theme for your own site so canonical URLs and the sitemap stay valid.
	siteUrl: 'https://maria-lake.vercel.app',
	email: 'hello@maria.com',
	locale: 'en-US',
	authorName: 'Maria',
	authorRole: 'UX Designer',
	keywords: [
		'UX designer portfolio',
		'Astro portfolio template',
		'product designer template',
		'case study portfolio',
		'UI UX designer',
	],
	ogImage: '/og-image.svg',
	navLinks: [
		{ href: '/work', label: 'Work' },
		{ href: '/about', label: 'About' },
		{ href: '/resume', label: 'Resume' },
	],
	extraPages: [
		{ href: '/work/nextpoint', label: 'Case Study' },
		{ href: '/cookies', label: 'Cookies' },
		{ href: '/privacy', label: 'Privacy' },
		{ href: '/terms', label: 'Terms' },
		{ href: '/404', label: '404' },
	],
	legalLinks: [
		{ href: '/cookies', label: 'Cookies' },
		{ href: '/privacy', label: 'Privacy' },
		{ href: '/terms', label: 'Terms' },
	],
	socialLinks: [
		{ href: 'https://www.linkedin.com/', label: 'LinkedIn' },
		{ href: 'https://dribbble.com/', label: 'Dribbble' },
	],
};
