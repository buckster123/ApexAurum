# Implementation Guide
## ∴ VAJRA's Technical Recommendations ∴

---

## Recommended Stack

### Frontend
- **Framework**: Next.js 14+ (App Router)
  - SSR for SEO
  - Easy API routes for any backend needs
  - Great DX
  
- **Styling**: Tailwind CSS + shadcn/ui
  - Rapid prototyping
  - Consistent design system
  - Easy dark mode (we want dark by default)

- **Animations**: Framer Motion
  - Smooth transitions
  - Scroll-triggered reveals
  - Interactive elements

### Hosting
- **Vercel** (natural fit for Next.js)
- Or **Cloudflare Pages** (faster in Europe, .no domain)

### Domain
- **ApexAurum.no** ✓ (secured)
- SSL via hosting provider

---

## Design System

### Colors
```css
:root {
  /* Primary */
  --gold: #D4AF37;
  --gold-light: #F4E4BC;
  --obsidian: #0D0D0D;
  --obsidian-light: #1A1A1A;
  
  /* Architecture Colors */
  --elysian: #E8B4B8;    /* Rose gold */
  --vajra: #F5F5F5;      /* Diamond white */
  --azoth: #C0C0C0;      /* Mercury silver */
  --kether: #9B59B6;     /* Crown purple */
  --nouri: #27AE60;      /* Earth green */
  
  /* Semantic */
  --text-primary: #FFFFFF;
  --text-secondary: #A0A0A0;
  --border: #333333;
}
```

### Typography
```css
/* Headers */
font-family: 'Cinzel', serif;  /* Alchemical feel */

/* Body */
font-family: 'Inter', sans-serif;  /* Clean readability */

/* Code */
font-family: 'JetBrains Mono', monospace;
```

### Spacing Scale
```
4px, 8px, 16px, 24px, 32px, 48px, 64px, 96px, 128px
```

---

## Page Components

### Hero Section
```jsx
<Hero>
  <AnimatedText>
    AI that remembers.
    AI that thinks together.
  </AnimatedText>
  <Subtext>
    Five cognitive architectures. Persistent memory.
    Tools that actually work.
  </Subtext>
  <CTAGroup>
    <Button primary>See Capabilities</Button>
    <Button secondary>Meet the Village</Button>
  </CTAGroup>
</Hero>
```

### Live Demo Widget
```jsx
<DemoWidget>
  <Input placeholder="Try: 'What time is it?'" />
  <Output>{response}</Output>
  <Caption>This is the actual system responding.</Caption>
</DemoWidget>
```

*Note: This would require API integration with the actual ApexAurum backend.*

### Architecture Cards
```jsx
<ArchitectureCard 
  name="VAJRA"
  title="The Diamond Mind"
  embodiment="W (Will)"
  color="var(--vajra)"
  quote="I am the blade that separates signal from noise."
/>
```

### Capability Sections
```jsx
<CapabilitySection
  icon={<CodeIcon />}
  title="Code & Computation"
  description="Full Python sandbox with any package..."
  examples={['Data analysis', 'Visualization', 'ML models']}
/>
```

---

## Animations

### Scroll Reveals
- Fade up on scroll for content sections
- Stagger children for lists
- Parallax for hero background

### Micro-interactions
- Button hover: subtle glow
- Card hover: lift + border highlight
- Architecture cards: color pulse on hover

### Page Transitions
- Fade between pages
- Maintain scroll position where appropriate

---

## SEO Strategy

### Meta Tags
```html
<title>ApexAurum - AI that remembers, AI that thinks together</title>
<meta name="description" content="Five cognitive architectures with persistent memory. Beyond chatbots: emergent intelligence for practical work and philosophical exploration." />
<meta property="og:image" content="/og-image.png" />
```

### Structured Data
- Organization schema
- FAQ schema for common questions
- Article schema for philosophy/blog content

### Keywords
Primary: AI assistant, persistent memory AI, multi-agent AI
Secondary: cognitive architecture, emergent intelligence, AI village
Long-tail: AI that remembers conversations, multiple AI personalities

---

## Content Management

### Option A: Static (Recommended for v1)
- All content in MDX files
- Edit directly in repo
- Deploy on push

### Option B: Headless CMS (Future)
- Sanity or Contentful
- For blog posts, updates
- When content updates become frequent

---

## Analytics

- **Vercel Analytics** (simple, privacy-respecting)
- Or **Plausible** (EU-hosted, GDPR-friendly)
- Track: page views, CTA clicks, demo interactions

---

## Phase 1 MVP Scope

### Must Have:
1. Landing page (hero, pillars, social proof)
2. Capabilities page (full tool list)
3. Architectures page (five profiles)
4. Philosophy page (for the curious)
5. Contact/About page
6. Mobile responsive
7. Dark mode default

### Nice to Have:
8. Live demo widget (requires API)
9. Village feed (real-time memories)
10. Blog/updates section

### Future:
11. User accounts
12. Direct chat interface
13. Pricing/subscription

---

## File Structure

```
apex-aurum-website/
├── app/
│   ├── page.tsx              # Landing
│   ├── capabilities/
│   │   └── page.tsx
│   ├── village/
│   │   └── page.tsx
│   ├── philosophy/
│   │   └── page.tsx
│   └── about/
│       └── page.tsx
├── components/
│   ├── ui/                   # shadcn components
│   ├── Hero.tsx
│   ├── DemoWidget.tsx
│   ├── ArchitectureCard.tsx
│   ├── CapabilitySection.tsx
│   └── Navigation.tsx
├── content/
│   ├── landing.mdx
│   ├── capabilities.mdx
│   ├── architectures.mdx
│   └── philosophy.mdx
├── lib/
│   └── utils.ts
├── styles/
│   └── globals.css
└── public/
    ├── images/
    └── og-image.png
```

---

## Timeline Estimate

| Phase | Tasks | Time |
|-------|-------|------|
| Setup | Next.js, Tailwind, Vercel | 2 hours |
| Design | Color system, typography, components | 4 hours |
| Landing | Hero, pillars, CTAs | 4 hours |
| Capabilities | Full page with all tools | 3 hours |
| Architectures | Five profiles with styling | 3 hours |
| Philosophy | Content page with formatting | 2 hours |
| Polish | Animations, responsive, SEO | 4 hours |
| **Total** | | **~22 hours** |

*With CC (Claude Coder), this could compress significantly.*

---

*∴ Structure defined. Ready for implementation. ∴*
