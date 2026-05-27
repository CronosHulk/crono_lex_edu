import { Link as RouterLink } from "react-router-dom";
import {
  ArrowRight,
  BookOpenCheck,
  BellRing,
  Bot,
  CheckCircle2,
  Clock3,
  FileText,
  Languages,
  Layers3,
  PlayCircle,
  Sparkles,
} from "lucide-react";
import {
  AppBar,
  Avatar,
  Box,
  Button,
  Chip,
  Container,
  Divider,
  LinearProgress,
  Paper,
  Stack,
  Toolbar,
  Typography,
} from "@mui/material";

const TELEGRAM_BOT_URL = "https://t.me/crono_lex_bot";

const featureCards = [
  {
    icon: <FileText />,
    title: "Імпорт власних слів",
    text: "Додавай слова з Google Doc, а CronoLex розкладе їх у чергу навчання.",
  },
  {
    icon: <BookOpenCheck />,
    title: "Тренування без хаосу",
    text: "Картки, переклад і вправи з пропусками працюють як один навчальний маршрут.",
  },
  {
    icon: <Languages />,
    title: "Український інтерфейс",
    text: "Підказки, помилки й навчальні тексти готові для web і Telegram.",
  },
  {
    icon: <BellRing />,
    title: "Нагадування в Telegram",
    text: "Обирай зручний час занять і отримуй м'яке нагадування, коли пора потренуватися.",
  },
];

const rhythmItems = [
  "Telegram підходить для коротких тренувань у дорозі, черзі або між справами",
  "Web-кабінет зручний для імпорту слів, налаштувань і занять у спокійному темпі",
  "Прогрес зберігається всюди, тому можна почати в чаті й продовжити на великому екрані",
];

export function LandingPage() {
  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "background.default", color: "text.primary" }}>
      <LandingHeader />
      <Box component="main">
        <HeroSection />
        <FeatureSection />
        <WorkflowSection />
        <FinalCtaSection />
      </Box>
    </Box>
  );
}

function LandingHeader() {
  return (
    <AppBar
      position="sticky"
      color="transparent"
      elevation={0}
      sx={{
        borderBottom: 1,
        borderColor: "divider",
        bgcolor: (theme) => theme.palette.mode === "dark" ? "rgba(17, 19, 24, 0.86)" : "rgba(255, 255, 255, 0.9)",
        backdropFilter: "blur(14px)",
      }}
    >
      <Container maxWidth="lg">
        <Toolbar disableGutters sx={{ minHeight: 68, gap: 2 }}>
          <Stack direction="row" spacing={1.25} sx={{ minWidth: 0, alignItems: "center" }}>
            <Avatar src="/cronolex_logo.jpg" alt="CronoLex" sx={{ width: 42, height: 42 }} />
            <Typography variant="h6" sx={{ fontWeight: 850, letterSpacing: 0 }}>
              CronoLex
            </Typography>
          </Stack>
          <Stack
            direction="row"
            spacing={1}
            sx={{ ml: "auto", display: { xs: "none", md: "flex" } }}
            aria-label="Landing navigation"
          >
            <Button href="#features" color="inherit">Можливості</Button>
            <Button href="#workflow" color="inherit">Як працює</Button>
            <Button href="#start" color="inherit">Старт</Button>
          </Stack>
          <Button component={RouterLink} to="/login" variant="outlined" sx={{ ml: { xs: "auto", md: 1 } }}>
            Увійти
          </Button>
        </Toolbar>
      </Container>
    </AppBar>
  );
}

function HeroSection() {
  return (
    <Box
      sx={{
        borderBottom: 1,
        borderColor: "divider",
        background: (theme) => theme.palette.mode === "dark"
          ? "linear-gradient(180deg, rgba(92, 200, 167, 0.08), rgba(17, 19, 24, 0) 62%)"
          : "linear-gradient(180deg, rgba(99, 91, 255, 0.08), rgba(255, 255, 255, 0) 62%)",
      }}
    >
      <Container
        maxWidth="lg"
        sx={{
          minHeight: { xs: "auto", md: "calc(100vh - 68px)" },
          py: { xs: 5, md: 8 },
          display: "grid",
          alignItems: "center",
          gridTemplateColumns: { xs: "1fr", lg: "minmax(0, 0.96fr) minmax(420px, 1.04fr)" },
          gap: { xs: 4, md: 6 },
        }}
      >
        <Stack spacing={3.2} sx={{ maxWidth: 590 }}>
          <Chip
            icon={<Sparkles size={16} />}
            label="Особистий словник + тренування"
            sx={{ alignSelf: "flex-start", "& .MuiChip-icon": { color: "primary.main" } }}
          />
          <Stack spacing={1.5}>
            <Typography
              variant="h1"
              sx={{
                fontSize: { xs: "2.65rem", sm: "3.35rem", md: "4.45rem" },
                lineHeight: 0.98,
                fontWeight: 900,
                letterSpacing: 0,
              }}
            >
              CronoLex
            </Typography>
            <Typography variant="h4" component="p" sx={{ fontWeight: 750, lineHeight: 1.16, maxWidth: 560 }}>
              Вчи англійські слова там, де вони справді з&apos;являються у твоєму житті.
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ fontSize: "1.08rem", lineHeight: 1.75, maxWidth: 560 }}>
              Імпортуй власний список, тренуй переклад і пропуски, а CronoLex нагадає в Telegram, коли час повернутися до заняття.
            </Typography>
          </Stack>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
            <Button
              component="a"
              href={TELEGRAM_BOT_URL}
              target="_blank"
              rel="noreferrer"
              variant="contained"
              size="large"
              startIcon={<Bot size={19} />}
              sx={{ minWidth: { sm: 196 } }}
            >
              Почати в Telegram
            </Button>
            <Button component={RouterLink} to="/login" variant="outlined" size="large" endIcon={<ArrowRight size={18} />} sx={{ minWidth: { sm: 196 } }}>
              Увійти в кабінет
            </Button>
          </Stack>
        </Stack>
        <ProductPreview />
      </Container>
    </Box>
  );
}

function ProductPreview() {
  return (
    <Paper
      variant="outlined"
      sx={{
        width: "100%",
        maxWidth: 620,
        justifySelf: { xs: "stretch", lg: "end" },
        p: { xs: 2, sm: 2.5 },
        borderRadius: 2,
        bgcolor: "background.paper",
        boxShadow: (theme) => theme.palette.mode === "dark" ? "0 24px 80px rgba(0,0,0,0.38)" : "0 24px 80px rgba(33,38,54,0.12)",
      }}
    >
      <Stack spacing={2.2}>
        <Stack direction="row" spacing={1.5} sx={{ alignItems: "center" }}>
          <Avatar src="/cronolex_logo.jpg" alt="" sx={{ width: 38, height: 38 }} />
          <Box sx={{ minWidth: 0 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 850 }}>Сьогоднішнє тренування</Typography>
            <Typography variant="body2" color="text.secondary">15 слів · A2 · web + Telegram</Typography>
          </Box>
          <Chip label="active" color="success" size="small" sx={{ ml: "auto" }} />
        </Stack>
        <Box
          sx={{
            p: { xs: 2, sm: 2.5 },
            borderRadius: 2,
            bgcolor: (theme) => theme.palette.mode === "dark" ? "rgba(92, 200, 167, 0.08)" : "rgba(99, 91, 255, 0.06)",
            border: 1,
            borderColor: "divider",
          }}
        >
          <Stack spacing={2}>
            <Stack direction="row" spacing={1} sx={{ minHeight: 22, alignItems: "center" }}>
              <PlayCircle size={18} color="currentColor" />
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 850, lineHeight: 1, textTransform: "uppercase" }}>
                Вправа 3 із 3
              </Typography>
            </Stack>
            <Typography variant="h5" sx={{ fontWeight: 850, lineHeight: 1.25 }}>
              She decided to ___ the meeting until Friday.
            </Typography>
            <PreviewAnswers />
          </Stack>
        </Box>
        <Stack spacing={1.2}>
          <Stack direction="row" spacing={2} sx={{ justifyContent: "space-between" }}>
            <Typography variant="body2" color="text.secondary">Прогрес сесії</Typography>
            <Typography variant="body2" sx={{ fontWeight: 800 }}>9 / 15</Typography>
          </Stack>
          <LinearProgress variant="determinate" value={60} sx={{ height: 8, borderRadius: 99 }} />
        </Stack>
        <Divider />
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
          <Metric icon={<Layers3 />} label="В черзі" value="124" />
          <Metric icon={<CheckCircle2 />} label="Вивчено" value="58" />
          <Metric icon={<Clock3 />} label="Повторити" value="17" />
        </Stack>
      </Stack>
    </Paper>
  );
}

function PreviewAnswers() {
  const answers = ["put off", "look after", "run into", "give up"];
  return (
    <Box sx={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 1 }}>
      {answers.map((answer, index) => (
        <Button
          key={answer}
          variant={index === 0 ? "contained" : "outlined"}
          color={index === 0 ? "success" : "inherit"}
          sx={{ minHeight: 46, justifyContent: "center" }}
        >
          {answer}
        </Button>
      ))}
    </Box>
  );
}

function Metric({ icon, label, value }) {
  return (
    <Box
      sx={{
        flex: 1,
        minWidth: 0,
        p: 1.5,
        border: 1,
        borderColor: "divider",
        borderRadius: 1.5,
        bgcolor: "background.default",
      }}
    >
      <Stack direction="row" spacing={1} sx={{ color: "text.secondary", alignItems: "center" }}>
        {icon}
        <Typography variant="caption" sx={{ fontWeight: 700 }}>{label}</Typography>
      </Stack>
      <Typography variant="h5" sx={{ mt: 0.5, fontWeight: 900 }}>{value}</Typography>
    </Box>
  );
}

function FeatureSection() {
  return (
    <Container id="features" maxWidth="lg" sx={{ py: { xs: 6, md: 9 } }}>
      <SectionTitle
        eyebrow="Можливості"
        title="Не просто список слів, а навчальний контур"
        text="Збирай власні слова, тренуй їх у зручному темпі й повертайся до повторення саме тоді, коли це має сенс."
      />
      <Box sx={{ mt: 4, display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(2, minmax(0, 1fr))" }, gap: 2 }}>
        {featureCards.map((feature) => (
          <Paper key={feature.title} variant="outlined" sx={{ p: 2.5, borderRadius: 2, height: "100%" }}>
            <Stack spacing={2}>
              <Box sx={{ color: "primary.main" }}>{feature.icon}</Box>
              <Stack spacing={0.8}>
                <Typography variant="h6" sx={{ fontWeight: 850 }}>{feature.title}</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.65 }}>{feature.text}</Typography>
              </Stack>
            </Stack>
          </Paper>
        ))}
      </Box>
    </Container>
  );
}

function WorkflowSection() {
  return (
    <Box id="workflow" sx={{ bgcolor: (theme) => theme.palette.mode === "dark" ? "rgba(255,255,255,0.025)" : "rgba(33,38,54,0.025)", borderY: 1, borderColor: "divider" }}>
      <Container maxWidth="lg" sx={{ py: { xs: 6, md: 9 }, display: "grid", gridTemplateColumns: { xs: "1fr", md: "0.82fr 1.18fr" }, gap: 4, alignItems: "center" }}>
        <SectionTitle
          eyebrow="Як працює"
          title="Telegram для навчання на ходу, web для спокійної роботи"
          text="Тренуйся короткими підходами в Telegram, коли є кілька вільних хвилин. А для імпорту, налаштувань і довших занять відкривай web-кабінет."
        />
        <Stack spacing={1.5}>
          {rhythmItems.map((item, index) => (
            <Paper key={item} variant="outlined" sx={{ p: 2, borderRadius: 2 }}>
              <Stack direction="row" spacing={2} sx={{ alignItems: "center" }}>
                <Box
                  sx={{
                    width: 34,
                    height: 34,
                    display: "grid",
                    placeItems: "center",
                    borderRadius: "50%",
                    bgcolor: "primary.main",
                    color: "primary.contrastText",
                    fontWeight: 900,
                    flexShrink: 0,
                  }}
                >
                  {index + 1}
                </Box>
                <Typography variant="body1" sx={{ fontWeight: 700 }}>{item}</Typography>
              </Stack>
            </Paper>
          ))}
        </Stack>
      </Container>
    </Box>
  );
}

function FinalCtaSection() {
  return (
    <Container id="start" maxWidth="lg" sx={{ py: { xs: 6, md: 8 } }}>
      <Paper
        variant="outlined"
        sx={{
          p: { xs: 3, md: 4 },
          borderRadius: 2,
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "1fr auto" },
          gap: 2.5,
          alignItems: "center",
        }}
      >
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 900, lineHeight: 1.15 }}>
            Готовий починати?
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mt: 1, maxWidth: 680 }}>
            Відкрий CronoLex у Telegram, створи профіль і продовжуй навчання там, де тобі зручніше.
          </Typography>
        </Box>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1.25}>
          <Button component={RouterLink} to="/login" variant="contained" size="large">
            Почати
          </Button>
          <Button component="a" href={TELEGRAM_BOT_URL} target="_blank" rel="noreferrer" variant="outlined" size="large">
            Telegram
          </Button>
        </Stack>
      </Paper>
    </Container>
  );
}

function SectionTitle({ eyebrow, title, text }) {
  return (
    <Stack spacing={1.2} sx={{ maxWidth: 720 }}>
      <Typography variant="overline" color="primary.main" sx={{ fontWeight: 900 }}>
        {eyebrow}
      </Typography>
      <Typography variant="h3" sx={{ fontSize: { xs: "2rem", md: "2.7rem" }, fontWeight: 900, lineHeight: 1.08 }}>
        {title}
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ lineHeight: 1.7 }}>
        {text}
      </Typography>
    </Stack>
  );
}
