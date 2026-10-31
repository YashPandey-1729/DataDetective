import type {AnchorHTMLAttributes} from 'react';

export default function EvidenceLink({id, children, ...props}: Omit<AnchorHTMLAttributes<HTMLAnchorElement>, 'href' | 'id'> & {id: string}) {
  return <a {...props} href={`#${id}`} onClick={event => {
    const target = document.getElementById(id);
    if (!target) return;
    event.preventDefault();
    if (target instanceof HTMLDetailsElement) target.open = true;
    const summary = target.querySelector('summary');
    summary?.focus({preventScroll: true});
    target.scrollIntoView({behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start'});
    history.replaceState(null, '', `#${id}`);
  }}>{children}</a>;
}
