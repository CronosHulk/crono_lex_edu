import React, { useEffect, useState } from "react";
import {
  AppBar,
  Avatar,
  Box,
  Button,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  MenuItem,
  Stack,
  TextField,
  Toolbar,
  Tooltip,
  Typography,
  useMediaQuery,
} from "@mui/material";
import { ChevronLeft, ChevronRight, LogOut, Menu, Moon, Sun, X } from "lucide-react";

export const DASHBOARD_DRAWER_WIDTH = 280;
export const LOCALE_OPTIONS = [
  { value: "uk", label: "UK" },
  { value: "ru", label: "RU" },
  { value: "pl", label: "PL" },
];

export function DashboardShell({
  user,
  active,
  title,
  subtitle,
  navItems,
  footerNavItems = [],
  mode,
  locale = "uk",
  brandSubtitle,
  versionLabel,
  accountLabel,
  accountBadge,
  labels,
  headerActions,
  footer,
  onToggleMode,
  onLocaleChange,
  localePending = false,
  onLogout,
  collapsible = false,
  LinkComponent,
  locationKey = "",
  children,
}) {
  const isDesktop = useMediaQuery("(min-width:900px)");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const text = normalizedShellLabels(labels);
  const desktopCollapsed = collapsible && isDesktop && collapsed;
  const desktopWidth = desktopCollapsed ? 76 : DASHBOARD_DRAWER_WIDTH;

  useEffect(() => {
    setMobileOpen(false);
  }, [locationKey]);

  const navigation = (
    <ShellNavigation
      user={user}
      navItems={navItems}
      footerNavItems={footerNavItems}
      active={active}
      collapsed={desktopCollapsed}
      brandSubtitle={brandSubtitle}
      versionLabel={versionLabel}
      accountLabel={accountLabel}
      accountBadge={accountBadge}
      labels={text}
      onLogout={onLogout}
      collapsible={collapsible && isDesktop}
      onToggleCollapse={() => setCollapsed((value) => !value)}
      onClose={() => setMobileOpen(false)}
      LinkComponent={LinkComponent}
    />
  );

  return (
    <Box sx={{ minHeight: "100vh", display: "flex", bgcolor: "background.default" }}>
      <Drawer
        variant="permanent"
        open
        sx={{
          display: { xs: "none", md: "block" },
          width: desktopWidth,
          flexShrink: 0,
          "& .MuiDrawer-paper": {
            width: desktopWidth,
            boxSizing: "border-box",
            borderRight: 1,
            borderColor: "divider",
            bgcolor: "background.paper",
            overflowX: "hidden",
          },
        }}
      >
        {navigation}
      </Drawer>
      <Drawer
        variant="temporary"
        open={!isDesktop && mobileOpen}
        onClose={() => setMobileOpen(false)}
        ModalProps={{ keepMounted: true }}
        sx={{
          display: { xs: "block", md: "none" },
          "& .MuiDrawer-paper": {
            width: "min(86vw, 320px)",
            boxSizing: "border-box",
            bgcolor: "background.paper",
          },
        }}
      >
        {navigation}
      </Drawer>

      <Box component="main" sx={{ minWidth: 0, flexGrow: 1, minHeight: "100vh", display: "flex", flexDirection: "column" }}>
        <AppBar
          position="sticky"
          color="transparent"
          elevation={0}
          sx={{
            top: 0,
            zIndex: (theme) => theme.zIndex.drawer - 1,
            borderBottom: 1,
            borderColor: "divider",
            bgcolor: "background.paper",
            backdropFilter: "blur(12px)",
          }}
        >
          <Toolbar sx={{ minHeight: { xs: 64, md: 72 }, px: { xs: 2, sm: 3 }, gap: 1.5 }}>
            <IconButton
              edge="start"
              aria-label={text.openMenu}
              onClick={() => setMobileOpen(true)}
              sx={{ display: { xs: "inline-flex", md: "none" } }}
            >
              <Menu />
            </IconButton>
            <Box sx={{ minWidth: 0, flex: 1 }}>
              <Typography variant="h5" component="h1" sx={{ fontWeight: 700, lineHeight: 1.15 }}>
                {title}
              </Typography>
              {subtitle && (
                <Typography variant="body2" color="text.secondary" sx={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {subtitle}
                </Typography>
              )}
            </Box>
            {headerActions}
            <Tooltip title={mode === "dark" ? text.lightTheme : text.darkTheme}>
              <IconButton
                onClick={onToggleMode}
                aria-label={mode === "dark" ? text.enableLightTheme : text.enableDarkTheme}
              >
                {mode === "dark" ? <Sun /> : <Moon />}
              </IconButton>
            </Tooltip>
            {onLocaleChange && (
              <TextField
                select
                size="small"
                value={locale}
                aria-label={text.interfaceLanguage}
                onChange={(event) => onLocaleChange(event.target.value)}
                disabled={localePending}
                sx={{
                  width: 82,
                  "& .MuiInputBase-input": {
                    py: 0.85,
                    fontWeight: 700,
                    textTransform: "uppercase",
                  },
                }}
              >
                {LOCALE_OPTIONS.map((option) => (
                  <MenuItem key={option.value} value={option.value}>{option.label}</MenuItem>
                ))}
              </TextField>
            )}
          </Toolbar>
        </AppBar>
        <Box
          sx={{
            width: "100%",
            maxWidth: 1440,
            mx: "auto",
            px: { xs: 2, sm: 3 },
            py: { xs: 2, sm: 3 },
            flex: 1,
            display: "flex",
            flexDirection: "column",
          }}
        >
          <Box sx={{ flex: "0 0 auto" }}>
            {children}
          </Box>
          {footer ? <Box sx={{ mt: "auto" }}>{footer}</Box> : null}
        </Box>
      </Box>
    </Box>
  );
}

function ShellNavigation({
  user,
  navItems,
  footerNavItems,
  active,
  collapsed,
  brandSubtitle,
  versionLabel,
  accountLabel,
  accountBadge,
  labels,
  onLogout,
  collapsible,
  onToggleCollapse,
  onClose,
  LinkComponent,
}) {
  return (
    <Stack sx={{ height: "100%" }}>
      <Stack direction="row" alignItems="center" spacing={1.25} sx={{ minHeight: 68, px: collapsed ? 1.25 : 2, py: 1.5 }}>
        <Avatar src="/cronolex_logo.jpg" alt="CronoLex" sx={{ width: 42, height: 42, bgcolor: "background.default" }} />
        {!collapsed && (
          <Box sx={{ minWidth: 0, flex: 1 }}>
            <Typography variant="body2" sx={{ fontWeight: 700, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              CronoLex
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {brandSubtitle}{versionLabel ? ` (${versionLabel})` : ""}
            </Typography>
          </Box>
        )}
        {collapsible && (
          <IconButton aria-label={collapsed ? labels.expandMenu : labels.collapseMenu} onClick={onToggleCollapse} sx={{ ml: collapsed ? 0 : "auto" }}>
            {collapsed ? <ChevronRight /> : <ChevronLeft />}
          </IconButton>
        )}
        {!collapsible && (
          <IconButton aria-label={labels.closeMenu} onClick={onClose} sx={{ display: { xs: "inline-flex", md: "none" }, ml: "auto" }}>
            <X />
          </IconButton>
        )}
      </Stack>
      <Box sx={{ borderBottom: 1, borderColor: "divider" }} />
      <List
        component="nav"
        sx={{
          display: "flex",
          flexDirection: "column",
          alignItems: "stretch",
          gap: 0.5,
          px: collapsed ? 1 : 1.5,
          py: 1.5,
          flex: 1,
          overflow: "auto",
        }}
      >
        {navItems.map((item) => (
          <ShellNavItem key={item.key} item={item} active={active} collapsed={collapsed} LinkComponent={LinkComponent} />
        ))}
      </List>
      <Box sx={{ borderBottom: 1, borderColor: "divider" }} />
      {footerNavItems.length ? (
        <Box sx={{ px: collapsed ? 1 : 1.5, py: 1.25, borderBottom: 1, borderColor: "divider" }}>
          <Stack spacing={0.75}>
            {footerNavItems.map((item) => (
              <ShellFooterNavItem key={item.key} item={item} active={active} collapsed={collapsed} LinkComponent={LinkComponent} />
            ))}
          </Stack>
        </Box>
      ) : null}
      <Stack direction="row" alignItems="center" spacing={1.25} sx={{ px: collapsed ? 1.25 : 2, py: 1.75, justifyContent: collapsed ? "center" : "flex-start" }}>
        <Avatar sx={{ width: 36, height: 36, bgcolor: "primary.main", color: "primary.contrastText", fontSize: 14 }}>
          {readUserInitials(user)}
        </Avatar>
        {!collapsed && (
          <>
            <Box sx={{ minWidth: 0, flex: 1 }}>
              <Stack direction="row" spacing={0.75} alignItems="center" sx={{ minWidth: 0 }}>
                {accountBadge}
                <Typography variant="body2" sx={{ minWidth: 0, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {user?.username ? `@${user.username}` : user?.telegram_user_id}
                </Typography>
              </Stack>
              <Stack direction="row" spacing={0.75} alignItems="center" sx={{ minWidth: 0 }}>
                <Typography variant="caption" color="text.secondary" sx={{ minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {accountLabel}
                </Typography>
              </Stack>
            </Box>
            <Tooltip title={labels.logout}>
              <IconButton aria-label={labels.logout} onClick={onLogout}>
                <LogOut />
              </IconButton>
            </Tooltip>
          </>
        )}
      </Stack>
    </Stack>
  );
}

function ShellFooterNavItem({ item, active, collapsed, LinkComponent }) {
  const isActive = active === item.key;
  const icon = React.cloneElement(item.icon, { size: collapsed ? 20 : 18 });

  if (collapsed) {
    return (
      <Tooltip title={item.label} placement="right">
        <IconButton
          {...linkProps(item.to, LinkComponent)}
          aria-label={item.label}
          sx={{
            width: 44,
            height: 44,
            color: isActive ? "primary.main" : "text.secondary",
            bgcolor: isActive ? "rgba(92, 200, 167, 0.12)" : "transparent",
          }}
        >
          {icon}
        </IconButton>
      </Tooltip>
    );
  }

  return (
    <Button
      {...linkProps(item.to, LinkComponent)}
      variant={isActive ? "contained" : "outlined"}
      color="primary"
      fullWidth
      startIcon={icon}
      sx={{ justifyContent: "flex-start", minHeight: 42, fontWeight: 700 }}
    >
      {item.label}
    </Button>
  );
}

function ShellNavItem({ item, active, collapsed, LinkComponent }) {
  const isActive = active === item.key;
  const isChildActive = item.children?.some((child) => child.key === active) || false;
  const isParentActive = isActive || isChildActive;
  const icon = React.cloneElement(item.icon, { size: 19 });
  const button = (
    <ListItemButton
      {...linkProps(item.to, LinkComponent)}
      selected={isParentActive}
      sx={{
        minHeight: 44,
        borderRadius: 1.5,
        px: collapsed ? 1.25 : 1.25,
        justifyContent: collapsed ? "center" : "flex-start",
        "&.Mui-selected": {
          color: "primary.main",
          bgcolor: "rgba(92, 200, 167, 0.12)",
        },
        "&.Mui-selected:hover": {
          bgcolor: "rgba(92, 200, 167, 0.16)",
        },
      }}
    >
      <ListItemIcon sx={{ color: "inherit", minWidth: collapsed ? 0 : 40 }}>{icon}</ListItemIcon>
      {!collapsed && (
        <>
          <ListItemText
            primary={item.label}
            primaryTypographyProps={{ fontSize: 14, fontWeight: isParentActive ? 700 : 600 }}
          />
          {item.children?.length ? <ChevronRight size={18} /> : null}
        </>
      )}
    </ListItemButton>
  );

  return (
    <Box sx={{ mb: 0.5 }}>
      {collapsed ? <Tooltip title={item.label} placement="right">{button}</Tooltip> : button}
      {isParentActive && !collapsed && item.children?.length ? (
        <Stack sx={{ pl: 6, pt: 0.75, gap: 0.25 }}>
          {item.children.map((child) => (
            <Typography
              key={child.to}
              {...linkProps(child.to, LinkComponent)}
              variant="body2"
              sx={{
                color: child.key === active ? "primary.main" : "text.secondary",
                textDecoration: "none",
                py: 0.55,
                fontWeight: child.key === active ? 700 : 600,
                "&:hover": { color: "primary.main" },
              }}
            >
              {child.label}
            </Typography>
          ))}
        </Stack>
      ) : null}
    </Box>
  );
}

function linkProps(to, LinkComponent) {
  if (LinkComponent) {
    return { component: LinkComponent, to };
  }
  return { component: "a", href: to };
}

function readUserInitials(user) {
  const source = user?.username || user?.first_name || user?.telegram_user_id || "CL";
  return String(source).slice(0, 2).toUpperCase();
}

function normalizedShellLabels(labels = {}) {
  return {
    openMenu: labels.openMenu || "Open menu",
    closeMenu: labels.closeMenu || "Close menu",
    lightTheme: labels.lightTheme || "Light theme",
    darkTheme: labels.darkTheme || "Dark theme",
    enableLightTheme: labels.enableLightTheme || "Enable light theme",
    enableDarkTheme: labels.enableDarkTheme || "Enable dark theme",
    interfaceLanguage: labels.interfaceLanguage || "Interface language",
    logout: labels.logout || "Logout",
    collapseMenu: labels.collapseMenu || "Collapse menu",
    expandMenu: labels.expandMenu || "Expand menu",
  };
}
