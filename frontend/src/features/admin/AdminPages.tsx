function StructuralAdminPage({
  title,
  sections = [],
  description,
}: {
  title: string
  sections?: string[]
  description?: string
}) {
  return (
    <section className="screen" aria-labelledby="page-title">
      <h1 id="page-title">{title}</h1>
      {description && <p>{description}</p>}
      {sections.length > 0 && (
        <div className="section-grid">
          {sections.map((section) => (
            <section className="structural-card" key={section}><h2>{section}</h2></section>
          ))}
        </div>
      )}
    </section>
  )
}

export const AdminPages = {
  Dashboard: () => <StructuralAdminPage title="Admin Dashboard" />,
  Lessons: () => <StructuralAdminPage title="Admin Lessons" />,
  LessonEditor: () => (
    <StructuralAdminPage
      title="Admin Lesson Editor"
      sections={['Lesson metadata', 'Vocabulary', 'Grammar', 'Exercises', 'Preview', 'Publish / Archive']}
    />
  ),
  Assessments: () => <StructuralAdminPage title="Admin Assessments" />,
  AssessmentEditor: () => (
    <StructuralAdminPage
      title="Admin Assessment Editor"
      description="Lifecycle structure: DRAFT → REVIEW → PUBLISHED"
    />
  ),
  Stats: () => <StructuralAdminPage title="Admin Stats" />,
}
