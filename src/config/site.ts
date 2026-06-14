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
	legalLinks: SiteLink[];
	socialLinks: SiteLink[];
};

const defaultSiteUrl = 'https://maria-lake.vercel.app';
const envSiteUrl = process.env.SITE_URL ?? process.env.PUBLIC_SITE_URL;
const normalizedSiteUrl = (envSiteUrl || defaultSiteUrl).replace(/\/+$/, '');

export const siteConfig: SiteConfig = {
	name: 'Home',
	title: 'Saurav Tripathy Portfolio',
	description:
		'TBD',
	// Set SITE_URL or PUBLIC_SITE_URL to keep canonicals, robots.txt, and the sitemap aligned in each environment.
	siteUrl: normalizedSiteUrl,
	email: 'sauravtripathy@yahoo.com',
	locale: 'en-US',
	authorName: 'Saurav',
	authorRole: 'AI Strategy & Product Builder',
	keywords: [
		'Astro UI UX portfolio theme',
		'UI UX designer portfolio template',
		'Astro portfolio template',
		'product designer portfolio theme',
		'case study portfolio theme',
	],
	ogImage: '/og-image.svg',
	navLinks: [
		{ href: '/About', label: 'About' },
		{ href: '/AI', label: 'AI' },
		{ href: '/MarTech', label: 'MarTech' },
		{ href: '/Projects', label: 'Projects' },
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
