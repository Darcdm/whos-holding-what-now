# Who's holding what now?

*New tools, shifting burdens and learning to keep up.* MoT London, November 2026.

**→ [darcdm.github.io/whos-holding-what-now](https://darcdm.github.io/whos-holding-what-now/)**

- [Slides](https://darcdm.github.io/whos-holding-what-now/slides/) with speaker notes (tap or swipe; the Notes button shows the notes)
- [Slides as a PDF](https://darcdm.github.io/whos-holding-what-now/slides/deck.pdf)
- [Reading list](https://darcdm.github.io/whos-holding-what-now/reading-list/)
- [The pad toolkit](https://darcdm.github.io/whos-holding-what-now/toolkit/)

All artwork is public domain; credits are in the slide notes.

---

### Updating the site

The source files live in my notes, not here. To publish changes:

```
python build.py          # rebuild slides, images, reading list, toolkit, PDF and offline cache
git add -A
git commit -m "Update slides"
git push
```

GitHub Pages picks it up about a minute later. Phones and iPads that have opened the site before get the new version on their next visit (or the one after, if they were offline).
