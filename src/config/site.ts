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

const defaultSiteUrl = 'https://www.saurav-tripathy.com';
const envSiteUrl = process.env.SITE_URL ?? process.env.PUBLIC_SITE_URL;
const normalizedSiteUrl = (envSiteUrl || defaultSiteUrl).replace(/\/+$/, '');

export const siteConfig: SiteConfig = {
	name: 'Saurav Tripathy',
	title: 'Saurav Tripathy Portfolio',
	description:
		'AI strategy & product portfolio of Saurav Tripathy — hands-on AI projects (a MarTech vendor-evaluation agent, a daily AI news decoder) and plain-English writing on AI in the enterprise.',
	// Set SITE_URL or PUBLIC_SITE_URL to keep canonicals, robots.txt, and the sitemap aligned in each environment.
	siteUrl: normalizedSiteUrl,
	email: 'sauravtripathy@yahoo.com',
	locale: 'en-US',
	authorName: 'Saurav Tripathy',
	authorRole: 'AI Strategy & Product Builder',
	keywords: [
		'Saurav Tripathy',
		'AI strategy',
		'MarTech AI',
		'AI product management',
		'vendor evaluation agent',
		'agentic AI',
		'LangGraph',
	],
	ogImage: '/og-image.svg',
	navLinks: [
		{ href: '/about', label: 'About' },
		{ href: '/ai', label: 'AI Understanding' },
		{ href: '/ai-in-enterprise', label: 'AI in Enterprise' },
		{ href: '/projects', label: 'AI Projects' },
	],
	extraPages: [],
		legalLinks: [
		{ href: '/cookies', label: 'Cookies' },
		{ href: '/privacy', label: 'Privacy' },
		{ href: '/terms', label: 'Terms' },
	],
	socialLinks: [
		{ href: 'https://github.com/SauravTripathy', label: 'GitHub' },
	],
};
