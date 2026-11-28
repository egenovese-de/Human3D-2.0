# Human3D M7 delivery report

**Qualified empirical prerelease** · Empirical Desktop v1 · version `0.3.0a7`

| Item | Value |
| --- | --- |
| Application branch | [development/m7](https://github.com/egenovese-de/Human3D-2.0/tree/development/m7) |
| Source commit | [`020fcc793e7417d6927d9e07346678e110ae9ddc`](https://github.com/egenovese-de/Human3D-2.0/commit/020fcc793e7417d6927d9e07346678e110ae9ddc) |
| Windows distribution | `Human3D-0.3.0a7-windows-020fcc793e74.zip` |
| Distribution SHA-256 | `5eb6b679c1a4477dfa393c45da0b38505be352399c96772df2661430570d9be3` |
| Backlog | 34/34 DONE |
| Remaining | None in the empirical software backlog |
| Default engine | A · M6 Baseline |
| Selectable engine | B · Geometry-driven experimental |
| Physical workstation | Pending Project Lead execution |

The Windows source distribution is separate from this evidence package. If starting from the existing checkout, use a linked worktree to keep local changes intact.

```powershell
Set-Location 'C:\Users\Asus\Documents\GitHub\Human3D-2.0'
git fetch origin development/m7
git worktree add --detach '..\Human3D-M7' 020fcc793e7417d6927d9e07346678e110ae9ddc
Set-Location '..\Human3D-M7'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Setup-Human3D.ps1
.\Launch-Human3D.cmd
```

In the extracted distribution, use the last two commands. Future launches use the CMD file directly. The empirical guide covers real-photo tests and evidence export. Review [qualification results](M7_QUALIFICATION_REPORT.md) and [known limitations](M7_KNOWN_LIMITATIONS.md). The evidence archive includes the visual walkthrough.
