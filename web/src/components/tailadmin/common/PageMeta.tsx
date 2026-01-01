import { HelmetProvider, Helmet } from "react-helmet-async";

interface PageMetaProps {
  title: string;
  description: string;
  // Open Graph meta tags for social media sharing
  ogTitle?: string;
  ogDescription?: string;
  ogImage?: string; // Must be absolute URL for social media platforms
  ogUrl?: string; // Must be absolute URL
  ogType?: string;
  // Twitter Card meta tags
  twitterCard?: "summary" | "summary_large_image" | "app" | "player";
  twitterSite?: string; // Twitter username (e.g., "@dumontcloud")
  twitterCreator?: string; // Twitter username of content creator
}

const PageMeta = ({
  title,
  description,
  ogTitle,
  ogDescription,
  ogImage,
  ogUrl,
  ogType = "website",
  twitterCard = "summary_large_image",
  twitterSite,
  twitterCreator,
}: PageMetaProps) => {
  // Use og values or fall back to base title/description
  const effectiveOgTitle = ogTitle || title;
  const effectiveOgDescription = ogDescription || description;

  return (
    <Helmet>
      <title>{title}</title>
      <meta name="description" content={description} />

      {/* Open Graph meta tags */}
      <meta property="og:title" content={effectiveOgTitle} />
      <meta property="og:description" content={effectiveOgDescription} />
      <meta property="og:type" content={ogType} />
      {ogUrl && <meta property="og:url" content={ogUrl} />}
      {ogImage && <meta property="og:image" content={ogImage} />}

      {/* Twitter Card meta tags */}
      <meta name="twitter:card" content={twitterCard} />
      <meta name="twitter:title" content={effectiveOgTitle} />
      <meta name="twitter:description" content={effectiveOgDescription} />
      {ogImage && <meta name="twitter:image" content={ogImage} />}
      {twitterSite && <meta name="twitter:site" content={twitterSite} />}
      {twitterCreator && <meta name="twitter:creator" content={twitterCreator} />}
    </Helmet>
  );
};

export const AppWrapper = ({ children }: { children: React.ReactNode }) => (
  <HelmetProvider>{children}</HelmetProvider>
);

export default PageMeta;
