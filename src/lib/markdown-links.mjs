import { withBase } from './site.mjs';

// Apply the hosting prefix to Markdown links and images, never code examples.
export const markdownLinks = {
  name: 'site-base-links',
  element: {
    filter: ['a', 'img'],
    visit(node, context) {
      for (const attribute of ['href', 'src']) {
        const value = node.properties?.[attribute];
        if (typeof value === 'string') context.setProperty(node, attribute, withBase(value));
      }
    },
  },
};
