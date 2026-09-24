export type SkillCategory =
  | "tech"
  | "cloud"
  | "soft"
  | "experience"
  | "education"
  | "domain";

export const CATEGORY_LABELS: Record<SkillCategory, string> = {
  tech: "技术栈",
  cloud: "云平台",
  soft: "软技能",
  experience: "经验要求",
  education: "学历资质",
  domain: "行业知识",
};

export const CATEGORY_ORDER: SkillCategory[] = [
  "tech",
  "cloud",
  "domain",
  "soft",
  "experience",
  "education",
];

interface TaxonEntry {
  keyword: string;
  category: SkillCategory;
  aliases?: string[];
}

export const SKILL_TAXONOMY: TaxonEntry[] = [
  // 云平台
  { keyword: "阿里云", category: "cloud", aliases: ["aliyun", "acs", "ack", "edas", "oss", "rds", "slb", "maxcompute"] },
  { keyword: "腾讯云", category: "cloud", aliases: ["tencent cloud", "tcloud", "cvm", "tke", "cos"] },
  { keyword: "AWS", category: "cloud", aliases: ["amazon web services", "ec2", "s3", "lambda", "eks"] },
  { keyword: "Azure", category: "cloud", aliases: ["microsoft azure"] },
  { keyword: "华为云", category: "cloud", aliases: ["huawei cloud", "hcs"] },
  { keyword: "GCP", category: "cloud", aliases: ["google cloud", "google cloud platform"] },

  // 技术栈
  { keyword: "Python", category: "tech", aliases: ["python3", "django", "flask", "fastapi"] },
  { keyword: "Java", category: "tech", aliases: ["spring", "springboot", "spring boot", "maven"] },
  { keyword: "Go", category: "tech", aliases: ["golang"] },
  { keyword: "Node.js", category: "tech", aliases: ["nodejs", "node js", "express", "nest"] },
  { keyword: "React", category: "tech", aliases: ["reactjs", "react js", "vite"] },
  { keyword: "Vue", category: "tech", aliases: ["vuejs", "vue js"] },
  { keyword: "TypeScript", category: "tech", aliases: ["ts"] },
  { keyword: "JavaScript", category: "tech", aliases: ["js", "es6"] },
  { keyword: "RAG", category: "tech", aliases: ["检索增强", "retrieval augmented", "rag"] },
  { keyword: "Agent", category: "tech", aliases: ["智能体", "ai agent", "multi-agent", "多智能体"] },
  { keyword: "LLM", category: "tech", aliases: ["大模型", "大语言模型", "gpt", "glm", "qwen", "通义"] },
  { keyword: "Docker", category: "tech", aliases: ["容器", "container"] },
  { keyword: "Kubernetes", category: "tech", aliases: ["k8s", "helm"] },
  { keyword: "微服务", category: "tech", aliases: ["microservice", "microservices"] },
  { keyword: "SQL", category: "tech", aliases: ["mysql", "postgresql", "postgres", "oracle"] },
  { keyword: "Redis", category: "tech" },
  { keyword: "MongoDB", category: "tech" },
  { keyword: "Elasticsearch", category: "tech", aliases: ["es", "elastic"] },
  { keyword: "Kafka", category: "tech" },
  { keyword: "Flink", category: "tech", aliases: ["flink流计算"] },
  { keyword: "Spark", category: "tech" },
  { keyword: "TensorFlow", category: "tech" },
  { keyword: "PyTorch", category: "tech" },
  { keyword: "Linux", category: "tech", aliases: ["shell", "bash"] },
  { keyword: "CI/CD", category: "tech", aliases: ["cicd", "jenkins", "gitlab ci", "github actions"] },

  // 软技能
  { keyword: "沟通能力", category: "soft", aliases: ["沟通", "communication"] },
  { keyword: "团队协作", category: "soft", aliases: ["协作", "teamwork", "collaboration"] },
  { keyword: "抗压能力", category: "soft", aliases: ["抗压", "pressure"] },
  { keyword: "学习能力", category: "soft", aliases: ["自驱", "self-motivated", "快速学习"] },
  { keyword: "责任心", category: "soft", aliases: ["负责", "responsibility"] },
  { keyword: "项目管理", category: "soft", aliases: ["project management", "pmp"] },
  { keyword: "文档能力", category: "soft", aliases: ["文档", "documentation"] },
  { keyword: "客户导向", category: "soft", aliases: ["客户意识", "customer"] },

  // 经验要求
  { keyword: "3年", category: "experience", aliases: ["三年", "3 years", "3+ years"] },
  { keyword: "5年", category: "experience", aliases: ["五年", "5 years", "5+ years"] },
  { keyword: "8年", category: "experience", aliases: ["八年", "8 years", "8+ years"] },
  { keyword: "10年", category: "experience", aliases: ["十年", "10 years", "10+ years"] },
  { keyword: "架构经验", category: "experience", aliases: ["架构设计经验"] },
  { keyword: "售前经验", category: "experience", aliases: ["pre-sales", "presales", "solution architect 经验"] },

  // 学历资质
  { keyword: "本科", category: "education", aliases: ["bachelor", "undergraduate"] },
  { keyword: "硕士", category: "education", aliases: ["master", "研究生"] },
  { keyword: "博士", category: "education", aliases: ["phd", "ph.d"] },
  { keyword: "PMP", category: "education" },
  { keyword: "ACP", category: "education", aliases: ["阿里云认证", "ace", "aca"] },
  { keyword: "TVP", category: "education", aliases: ["腾讯云认证"] },

  // 行业知识
  { keyword: "教育", category: "domain", aliases: ["教育行业", "edtech"] },
  { keyword: "医疗", category: "domain", aliases: ["医疗行业", "healthcare", "智慧医疗"] },
  { keyword: "金融", category: "domain", aliases: ["金融行业", "fintech"] },
  { keyword: "政企", category: "domain", aliases: ["政务", "toG", "to B", "toB"] },
  { keyword: "制造业", category: "domain", aliases: ["工业", "manufacturing"] },
];
